import { EditorSelection } from "@codemirror/state";
import { CodeMirrorRef } from "./CodeMirror";

type EditorCommand = {
  label: string;
  icon: string;
  onClick: (codeMirror: CodeMirrorRef) => void;
};

export const boldCommand: EditorCommand = {
  label: "Add bold text",
  icon: "mdi:format-bold",
  onClick: ({ view }) => {
    if (!view) return;

    view.dispatch(
      view.state.changeByRange((range) => ({
        changes: [
          { from: range.from, insert: "**" },
          { from: range.to, insert: "**" },
        ],
        range: EditorSelection.range(range.from + 2, range.to + 2),
      }))
    );
  },
};
