import React, { forwardRef, useRef, useState } from "react";
import { MarkdownViewer } from "../MarkdownViewer";
import { classNames } from "../../utils/common";
import { EditorHeader } from "./MarkdownEditorHeader";
import { CodeMirror, CodeMirrorRef } from "./CodeMirror";

type MarkdownEditorProps = {
  className?: string;
  onChange: (v: string) => void;
  value?: string;
};
export const MarkdownEditor = forwardRef<HTMLDivElement, MarkdownEditorProps>(
  ({ className = "", onChange, value }, ref) => {
    const [preview, setPreview] = useState<boolean>(false);
    const codeMirror = useRef<CodeMirrorRef>({ editor: null });

    return (
      <div ref={ref} className={classNames("rounded-md border border-gray-300 shadow", className)}>
        <EditorHeader
          codeMirror={codeMirror.current}
          preview={preview}
          onPreviewToggle={() => setPreview(!preview)}
        />

        {preview ? (
          <MarkdownViewer value={value} />
        ) : (
          <CodeMirror
            placeholder="Write your text here..."
            value={value}
            onChange={onChange}
            ref={codeMirror}
          />
        )}
      </div>
    );
  }
);
