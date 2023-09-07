import { gql } from "@apollo/client";
import { ChatBubbleLeftIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useAtom } from "jotai";
import { useContext, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "../../components/button";
import { BUTTON_TYPES, RoundedButton } from "../../components/rounded-button";
import { SidePanelTitle } from "../../components/sidepanel-title";
import SlideOver from "../../components/slide-over";
import { Tooltip } from "../../components/tooltip";
import {
  PROPOSED_CHANGES_OBJECT_THREAD,
  PROPOSED_CHANGES_OBJECT_THREAD_OBJECT,
} from "../../config/constants";
import { AuthContext } from "../../decorators/withAuth";
import { getProposedChangesObjectThreads } from "../../graphql/queries/proposed-changes/getProposedChangesObjectThreads";
import useQuery from "../../hooks/useQuery";
import { schemaState } from "../../state/atoms/schema.atom";
import { getThreadLabel, getThreadTitle } from "../../utils/diff";
import { DiffContext } from "./data-diff";
import { DataDiffComments } from "./diff-comments";

type tDataDiffThread = {
  path: string;
};

export const DataDiffThread = (props: tDataDiffThread) => {
  const { path } = props;

  const { proposedchange } = useParams();
  const [schemaList] = useAtom(schemaState);
  const auth = useContext(AuthContext);
  const { node, currentBranch } = useContext(DiffContext);
  const [showThread, setShowThread] = useState(false);

  const schemaData = schemaList.filter((s) => s.name === PROPOSED_CHANGES_OBJECT_THREAD)[0];

  const queryString = schemaData
    ? getProposedChangesObjectThreads({
        id: proposedchange,
        path,
        kind: schemaData.kind,
      })
    : // Empty query to make the gql parsing work
      // TODO: Find another solution for queries while loading schemaData
      "query { ok }";

  const query = gql`
    ${queryString}
  `;

  const { loading, error, data, refetch } = useQuery(query, { skip: !schemaData });

  const thread = data ? data[PROPOSED_CHANGES_OBJECT_THREAD_OBJECT]?.edges[0]?.node : {};

  if (loading || error) {
    return null;
  }

  const title = (
    <SidePanelTitle title="Conversation" hideBranch>
      {getThreadTitle(thread, getThreadLabel(node, currentBranch, path))}
    </SidePanelTitle>
  );

  return (
    <div className="ml-2">
      {thread?.comments?.count && (
        <div className="flex items-center cursor-pointer">
          <ChatBubbleLeftIcon className="h-5 w-5 mr-1" />
          <Tooltip message={"Add comment"}>
            <RoundedButton
              disabled={!auth?.permissions?.write}
              onClick={() => {
                setShowThread(true);
              }}
              className="p-0 px-2"
              type={BUTTON_TYPES.DEFAULT}>
              {/* Display either a pill with the number of comments, or a plus icon to add a comment */}
              {thread?.comments?.count}
            </RoundedButton>
          </Tooltip>
        </div>
      )}

      {!thread?.comments?.count && (
        <div className="cursor-pointer hidden group-hover:block">
          <Tooltip message={"Add comment"}>
            <RoundedButton
              disabled={!auth?.permissions?.write}
              onClick={() => {
                setShowThread(true);
              }}
              className="p-1"
              type={BUTTON_TYPES.DEFAULT}>
              {/* Display either a pill with the number of comments, or a plus icon to add a comment */}
              <PlusIcon className="h-4 w-4 " aria-hidden="true" />
            </RoundedButton>
          </Tooltip>
        </div>
      )}

      <SlideOver title={title} open={showThread} setOpen={setShowThread}>
        <DataDiffComments path={path} refetch={refetch} />

        <div className="flex items-center justify-end gap-x-6 py-3 pr-3 border-t">
          <Button onClick={() => setShowThread(false)}>Close</Button>
        </div>
      </SlideOver>
    </div>
  );
};