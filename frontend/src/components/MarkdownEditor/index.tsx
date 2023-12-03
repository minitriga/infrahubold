import { Button } from "../button";
import React, { forwardRef, useEffect, useRef, useState } from "react";
import { EditorView, keymap, placeholder as placeholderView } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { indentWithTab } from "@codemirror/commands";
import { markdown, markdownLanguage } from "@codemirror/lang-markdown";
import { MarkdownViewer } from "../MarkdownViewer";

const EditorHeader = ({ preview, onPreviewToggle }) => (
  <div className="border-b">
    <Button onClick={onPreviewToggle} className="bg-white border-none rounded-none rounded-tl-md">
      {preview ? "Continue editing" : "Preview"}
    </Button>
  </div>
);

const CodeMirror = ({ value = "", placeholder = "Write your text here...", onChange }) => {
  const editor = useRef<HTMLDivElement>(null);

  const onUpdate = EditorView.updateListener.of(({ state }) => {
    onChange(state.doc.toString());
  });

  useEffect(() => {
    const startState = EditorState.create({
      doc: value,
      extensions: [
        EditorView.baseTheme({
          "&.cm-focused": {
            outline: "none",
          },
        }),
        keymap.of([indentWithTab]),
        markdown({ base: markdownLanguage }),
        onUpdate,
        placeholderView(placeholder),
      ],
    });

    const view = new EditorView({ state: startState, parent: editor.current! });

    view.focus();
    return () => {
      view.destroy();
    };
  }, []);

  return <div ref={editor}></div>;
};

type MarkdownEditorProps = {
  onChange: Function;
  value?: string;
};
export const MarkdownEditor = forwardRef<HTMLDivElement, MarkdownEditorProps>(
  ({ onChange, value }, ref) => {
    const [preview, setPreview] = useState<boolean>(false);

    return (
      <div ref={ref} className="relative rounded-md border border-gray-300 shadow">
        <EditorHeader preview={preview} onPreviewToggle={() => setPreview(!preview)} />

        {preview ? (
          <MarkdownViewer value={value} />
        ) : (
          <CodeMirror placeholder="Write your text here..." value={value} onChange={onChange} />
        )}
      </div>
    );
  }
);
