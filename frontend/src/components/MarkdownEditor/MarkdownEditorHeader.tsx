import React, { FC } from "react";
import { Button } from "../button";
import {
  boldCommand,
  italicCommand,
  orderedListCommand,
  strikethroughCommand,
  unorderedListCommand,
} from "./command";
import { Icon } from "@iconify-icon/react";
import { CodeMirrorRef } from "./CodeMirror";

type ToolbarProps = { codeMirror: CodeMirrorRef };

const ToolBar: FC<ToolbarProps> = ({ codeMirror }) => {
  return (
    <div className="flex items-center gap-2 pr-2">
      {[
        boldCommand,
        italicCommand,
        strikethroughCommand,
        unorderedListCommand,
        orderedListCommand,
      ].map(({ label, icon, onClick }, key) => {
        let buttonProps: React.ButtonHTMLAttributes<HTMLButtonElement> = {
          className: "bg-white border-none p-0 text-xl shadow-none",
          type: "button",
          "aria-label": label,
          onMouseDown: (event) => {
            event.preventDefault();
            if (codeMirror) onClick(codeMirror);
          },
        };

        return (
          <Button {...buttonProps} key={key}>
            <Icon icon={icon} />
          </Button>
        );
      })}
    </div>
  );
};

type EditorHeaderProps = {
  codeMirror: CodeMirrorRef;
  preview: boolean;
  onPreviewToggle: Function;
};

export const EditorHeader: FC<EditorHeaderProps> = ({ codeMirror, preview, onPreviewToggle }) => (
  <div className="border-b flex justify-between overflow-auto">
    <Button onClick={onPreviewToggle} className="bg-white border-none rounded-none rounded-tl-md">
      {preview ? "Continue editing" : "Preview"}
    </Button>

    {!preview && <ToolBar codeMirror={codeMirror} />}
  </div>
);
