import { useCallback, useEffect, useState } from "react";
import { toast } from "react-toastify";
import LoadingScreen from "../screens/loading-screen/loading-screen";
import NoDataFound from "../screens/no-data-found/no-data-found";
import { fetchStream } from "../utils/fetch";
import { ALERT_TYPES, Alert } from "./alert";

type tFile = {
  url: string;
};

export const File = (props: tFile) => {
  const { url } = props;

  const [isLoading, setIsLoading] = useState(false);
  const [fileContent, setFileContent] = useState("");

  const fetchFileDetails = useCallback(async () => {
    if (!url) return;

    setIsLoading(true);

    try {
      const fileResult = await fetchStream(url);

      setFileContent(fileResult);
    } catch (err) {
      console.error("err: ", err);
      toast(<Alert type={ALERT_TYPES.ERROR} message="Error while loading file content" />);
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    fetchFileDetails();
  }, []);

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!fileContent) {
    return <NoDataFound />;
  }

  return (
    <pre className="m-4 p-4 bg-custom-white rounded-md whitespace-pre-wrap">{fileContent}</pre>
  );
};