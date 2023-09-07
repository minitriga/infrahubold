import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { useContext, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "react-toastify";
import { StringParam, useQueryParam } from "use-query-params";
import { ALERT_TYPES, Alert } from "../../components/alert";
import { BUTTON_TYPES, Button } from "../../components/button";
import { CONFIG } from "../../config/config";
import { QSP } from "../../config/qsp";
import { AuthContext } from "../../decorators/withAuth";
import { classNames } from "../../utils/common";
import { fetchUrl } from "../../utils/fetch";

type tGenerateProps = {
  label?: string;
  artifactid?: string;
  definitionid?: string;
};

export const Generate = (props: tGenerateProps) => {
  const { label, artifactid, definitionid } = props;

  const { objectid } = useParams();

  const [branch] = useQueryParam(QSP.BRANCH, StringParam);
  const [at] = useQueryParam(QSP.DATETIME, StringParam);
  const [isLoading, setIsLoading] = useState(false);

  const auth = useContext(AuthContext);

  const handleGenerate = async () => {
    try {
      setIsLoading(true);

      const url = CONFIG.ARTIFACTS_GENERATE_URL(definitionid || objectid);

      const options: string[][] = [
        ["branch", branch ?? ""],
        ["at", at ?? ""],
      ].filter(([, v]) => v !== undefined && v !== "");

      const qsp = new URLSearchParams(options);

      const urlWithQsp = `${url}${options.length ? `&${qsp.toString()}` : ""}`;

      await fetchUrl(urlWithQsp, {
        method: "POST",
        headers: {
          authorization: `Bearer ${auth.accessToken}`,
        },
        ...(artifactid ? { body: JSON.stringify({ nodes: [artifactid] }) } : {}),
      });

      if (artifactid) {
        toast(<Alert message="Artifact re-generated" type={ALERT_TYPES.SUCCESS} />);
      } else {
        toast(<Alert message="Artifacts generated" type={ALERT_TYPES.SUCCESS} />);
      }

      setIsLoading(false);
    } catch (error) {
      console.error("error: ", error);
      toast(
        <Alert message="An error occured while generating the artifact" type={ALERT_TYPES.ERROR} />
      );
      setIsLoading(false);
    }
  };

  return (
    <Button
      disabled={!auth?.permissions?.write || isLoading}
      onClick={handleGenerate}
      className="mr-4"
      buttonType={BUTTON_TYPES.VALIDATE}>
      {label ?? "Generate"}
      <ArrowPathIcon
        className={classNames("-mr-0.5 h-4 w-4", isLoading ? "animate-spin" : "")}
        aria-hidden="true"
      />
    </Button>
  );
};