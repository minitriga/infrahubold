import React, { useRef, useState } from "react";
import { classNames } from "../utils/common";
import { useClickOutside } from "../hooks/useClickOutside";
import { MarkdownEditor } from "./MarkdownEditor";

export function TextareaWithEditor({
  className,
  onChange,
  value,
  error,
  isProtected,
  isOptional,
  disabled,
  ...otherProps
}) {
  const [text, setText] = useState(value);
  const [editorOpen, setEditorOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setEditorOpen(!editorOpen));

  return (
    <div className="relative">
      {editorOpen ? (
        <MarkdownEditor
          ref={ref}
          onChange={(e) => {
            onChange(e);
            setText(e);
          }}
          value={text}
          className="min-h-16"
        />
      ) : (
        <textarea
          rows={2}
          onChange={(e) => onChange(e.target.value)}
          defaultValue={text}
          onFocus={() => setEditorOpen(!editorOpen)}
          className={classNames(
            `
                block w-full rounded-md border-0 p-2 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400
                border-gray-300 bg-custom-white
                sm:text-sm sm:leading-6
                focus:ring-2 focus:ring-inset focus:ring-custom-blue-600 focus:border-custom-blue-600 focus:outline-none
                disabled:cursor-not-allowed disabled:bg-gray-100 min-h-16
            `,
            className ?? "",
            error?.message ? "ring-red-500 focus:ring-red-600" : ""
          )}
          {...otherProps}
        />
      )}

      {error?.message && (
        <div className="absolute text-sm text-red-500 bg-custom-white -bottom-2 ml-2 px-2">
          {error.message}
        </div>
      )}
    </div>
  );
}
