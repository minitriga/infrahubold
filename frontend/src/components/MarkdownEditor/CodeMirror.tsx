import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { EditorView, keymap, placeholder as placeholderView } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { indentWithTab, defaultKeymap } from "@codemirror/commands";
import { markdown, markdownLanguage } from "@codemirror/lang-markdown";

export interface CodeMirrorRef {
  editor?: HTMLDivElement | null;
  state?: EditorState;
  view?: EditorView;
}

type CodeMirrorProps = {
  value?: string;
  placeholder?: string;
  onChange: (s: string) => void;
};

export const CodeMirror = forwardRef<CodeMirrorRef, CodeMirrorProps>(
  ({ value = "", placeholder = "Write your text here...", onChange }, ref) => {
    const editor = useRef<HTMLDivElement>(null);
    const [state, setState] = useState<EditorState>();
    const [view, setView] = useState<EditorView>();

    useImperativeHandle(ref, () => ({ editor: editor.current, state, view }));
    const theme = EditorView.baseTheme({
      "&.cm-focused": {
        outline: "none",
      },
    });
    const onUpdate = EditorView.updateListener.of(({ state }) => {
      onChange(state.doc.toString());
    });

    useEffect(() => {
      const startState = EditorState.create({
        doc: value,
        extensions: [
          theme,
          keymap.of([...defaultKeymap, indentWithTab]),
          markdown({ base: markdownLanguage }),
          onUpdate,
          placeholderView(placeholder),
        ],
      });

      const view = new EditorView({ state: startState, parent: editor.current! });

      setState(startState);
      setView(view);
      view.focus();
      return () => {
        view.destroy();
      };
    }, []);

    return <div ref={editor}></div>;
  }
);
