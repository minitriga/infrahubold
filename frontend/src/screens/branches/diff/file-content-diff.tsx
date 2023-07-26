import { gql } from "@apollo/client";
import { PencilIcon } from "@heroicons/react/24/outline";
import { useAtom } from "jotai";
import { useCallback, useEffect, useState } from "react";
import { Diff, Hunk, getChangeKey, parseDiff } from "react-diff-view";
import "react-diff-view/style/index.css";
import { useParams } from "react-router-dom";
import { toast } from "react-toastify";
import sha from "sha1";
import { diffLines, formatLines } from "unidiff";
import { StringParam, useQueryParam } from "use-query-params";
import Accordion from "../../../components/accordion";
import { ALERT_TYPES, Alert } from "../../../components/alert";
import { Button } from "../../../components/button";
import { AddComment } from "../../../components/conversations/add-comment";
import { Thread } from "../../../components/conversations/thread";
import { CONFIG } from "../../../config/config";
import { PROPOSED_CHANGES_FILE_THERAD } from "../../../config/constants";
import { QSP } from "../../../config/qsp";
import { getProposedChangesFilesThreads } from "../../../graphql/queries/proposed-changes/getProposedChangesFilesThreads";
import useQuery from "../../../hooks/useQuery";
import { schemaState } from "../../../state/atoms/schema.atom";
import { fetchStream } from "../../../utils/fetch";
import ErrorScreen from "../../error-screen/error-screen";
import LoadingScreen from "../../loading-screen/loading-screen";

const fakeIndex = () => {
  return sha(Math.random() * 100000).slice(0, 9);
};

const appendGitDiffHeaderIfNeeded = (diffText: string) => {
  if (diffText.startsWith("diff --git")) {
    return diffText;
  }

  const segments = ["diff --git a/a b/b", `index ${fakeIndex()}..${fakeIndex()} 100644`, diffText];

  return segments.join("\n");
};

const shouldDisplayAddComment = (state: any, change: any) => {
  const { side, newLineNumber, oldLineNumber, lineNumber, isInsert, isDelete } = state;

  if (side === "new") {
    return (
      (newLineNumber && newLineNumber === change.newLineNumber) ||
      (lineNumber && lineNumber === change.lineNumber && isInsert === change.isInsert)
    );
  }

  return (
    (oldLineNumber && oldLineNumber === change.oldLineNumber) ||
    (lineNumber && lineNumber === change.lineNumber && isDelete === change.isDelete)
  );
};

const getThread = (threads: any[], change: any, commitFrom?: string, commitTo?: string) => {
  const thread = threads.find((thread) => {
    const theradLineNumber = thread?.line_number?.value;

    if (
      change?.isDelete &&
      thread?.commit?.value === commitFrom &&
      theradLineNumber === change.lineNumber
    ) {
      return true;
    }

    if (
      change?.isInsert &&
      thread?.commit?.value === commitTo &&
      theradLineNumber === change.lineNumber
    ) {
      return true;
    }

    if (change.isNormal && theradLineNumber === change.newLineNumber) {
      return true;
    }

    return false;
  });

  return thread;
};

export const FileContentDiff = (props: any) => {
  const { repositoryId, file, commitFrom, commitTo } = props;

  const { proposedchange } = useParams();
  const [branchOnly] = useQueryParam(QSP.BRANCH_FILTER_BRANCH_ONLY, StringParam);
  const [timeFrom] = useQueryParam(QSP.BRANCH_FILTER_TIME_FROM, StringParam);
  const [timeTo] = useQueryParam(QSP.BRANCH_FILTER_TIME_TO, StringParam);
  const [schemaList] = useAtom(schemaState);
  const [isLoading, setIsLoading] = useState(false);
  const [previousFile, setPreviousFile] = useState(false);
  const [newFile, setNewFile] = useState(false);
  const [displayAddComment, setDisplayAddComment] = useState<any>({});

  const schemaData = schemaList.filter((s) => s.name === PROPOSED_CHANGES_FILE_THERAD)[0];

  const queryString = schemaData
    ? getProposedChangesFilesThreads({
        id: proposedchange,
        kind: schemaData.kind,
      })
    : // Empty query to make the gql parsing work
      // TODO: Find another solution for queries while loading schemaData
      "query { ok }";

  const query = gql`
    ${queryString}
  `;

  const { loading, error, data, refetch } = useQuery(query, { skip: !schemaData });

  const threads = data ? data[schemaData?.kind]?.edges?.map((edge: any) => edge.node) : [];

  const fetchFileDetails = useCallback(async (commit: string, setState: Function) => {
    setIsLoading(true);

    try {
      const url = CONFIG.FILES_CONTENT_URL(repositoryId, file.location);

      const options: string[][] = [
        ["branch_only", branchOnly ?? ""],
        ["time_from", timeFrom ?? ""],
        ["time_to", timeTo ?? ""],
        ["commit", commit ?? ""],
      ].filter(([, v]) => v !== undefined && v !== "");

      const qsp = new URLSearchParams(options);

      const urlWithQsp = `${url}?${options.length ? `&${qsp.toString()}` : ""}`;

      const fileResult = await fetchStream(urlWithQsp);

      setState(fileResult);
    } catch (err) {
      console.error("err: ", err);
      toast(<Alert type={ALERT_TYPES.ERROR} message="Error while loading files diff" />);
    }

    setIsLoading(false);
  }, []);

  const setFileDetailsInState = useCallback(async () => {
    await fetchFileDetails(commitFrom, setPreviousFile);
    await fetchFileDetails(commitTo, setNewFile);
  }, []);

  useEffect(() => {
    setFileDetailsInState();
  }, []);

  const handleSubmitComment = () => {
    //
  };

  const handleCloseComment = () => {
    setDisplayAddComment({});
  };

  const getWidgets = (hunks: any) => {
    const changes = hunks.reduce((result: any, { changes }: any) => [...result, ...changes], []);

    return changes.reduce((widgets: any, change: any) => {
      const changeKey = getChangeKey(change);

      if (shouldDisplayAddComment(displayAddComment, change)) {
        return {
          ...widgets,
          [changeKey]: <AddComment onSubmit={handleSubmitComment} onClose={handleCloseComment} />,
        };
      }

      const thread = getThread(threads, change, commitFrom, commitTo);

      if (thread) {
        return {
          ...widgets,
          [changeKey]: <Thread thread={thread} refetch={refetch} />,
        };
      }

      if (!change.comments) {
        return widgets;
      }

      return {
        ...widgets,
        [changeKey]: change?.comments?.map((comment: any, index: number) => (
          <div
            key={index}
            className="bg-custom-white p-4 border border-custom-blue-500 rounded-md m-2">
            {comment.message}
          </div>
        )),
      };
    }, {});
  };

  const renderGutter = (options: any) => {
    const { renderDefault, wrapInAnchor, inHoverState, side, change } = options;

    const handleClick = () => {
      setDisplayAddComment({ side, ...change });
    };

    return (
      <>
        {wrapInAnchor(renderDefault())}

        {inHoverState && (
          <Button
            className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
            onClick={handleClick}>
            <PencilIcon className="w-3 h-3" />
          </Button>
        )}
      </>
    );
  };

  if (loading || isLoading) {
    return <LoadingScreen />;
  }

  if (error) {
    return <ErrorScreen />;
  }

  if (!previousFile && !newFile) {
    return null;
  }

  const diff = formatLines(diffLines(previousFile, newFile), {
    context: 3,
    aname: commitFrom,
    bname: commitTo,
  });

  const [fileContent] = parseDiff(appendGitDiffHeaderIfNeeded(diff), {
    nearbySequences: "zip",
  });

  return (
    <div className={"rounded-lg shadow p-4 m-4 bg-custom-white"}>
      <Accordion title={file.location}>
        <div className="flex">
          <div className="flex-1">
            {commitFrom && <span className="font-normal italic">Commit: {commitFrom}</span>}
          </div>

          <div className="flex-1">
            {commitTo && <span className="font-normal italic">Commit: {commitTo}</span>}
          </div>
        </div>

        <div className="bg-gray-50">
          <Diff
            key={`${sha(diff)}${previousFile ? sha(previousFile) : ""}`}
            hunks={fileContent.hunks}
            viewType="split"
            diffType={fileContent.type}
            renderGutter={renderGutter}
            widgets={getWidgets(fileContent.hunks)}
            optimizeSelection>
            {(hunks) => hunks.map((hunk) => <Hunk key={hunk.content} hunk={hunk} />)}
          </Diff>
        </div>
      </Accordion>
    </div>
  );
};
