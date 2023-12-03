import React, { FC } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "../styles/markdown.css";

type MarkdownViewerProps = {
  value: string;
};

export const MarkdownViewer: FC<MarkdownViewerProps> = ({ value }) => {
  return (
    <Markdown remarkPlugins={[remarkGfm]} className="markdown">
      {value}
    </Markdown>
  );
};
