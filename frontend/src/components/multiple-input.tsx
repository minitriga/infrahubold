import React from "react";
import { classNames } from "../utils/common";
import { Badge } from "./badge";
import { SelectOption } from "./select";

type MultipleInputProps = {
  value: SelectOption[] | undefined;
  onChange: (item: SelectOption[] | undefined) => void;
  className?: string;
};

// Forward ref used for Combobox.Input in Select
export const MultipleInput = React.forwardRef(
  (props: MultipleInputProps, ref: any) => {
    const { className, onChange, value } = props;

    // Remove item from list
    const handleDelete = (item: SelectOption) => {
      const newValue = value?.filter((v: SelectOption) => v.id !== item.id);

      return onChange(newValue);
    };

    return (
      <div
        className={classNames(
          `flex w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 h-[36px]
          border-gray-300 bg-white
          sm:text-sm sm:leading-6 px-2
          focus:ring-2 focus:ring-inset focus:ring-indigo-600 focus:border-indigo-600 focus:outline-none
          disabled:cursor-not-allowed disabled:bg-gray-100
        `,
          className ?? ""
        )}
      >
        {value?.map((item: SelectOption, index: number) => (
          <Badge key={index} value={item} onDelete={handleDelete}>
            {item.name}
          </Badge>
        ))}
      </div>
    );
  }
);
