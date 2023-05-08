import { useState } from "react";
import {
  FieldValues,
  RegisterOptions,
  UseFormRegister,
  UseFormSetValue,
} from "react-hook-form";
import { SelectOption } from "../components/select";
import { FormFieldError } from "../screens/edit-form-hook/form";
import OpsMultiSelect from "./multi-select";

interface Props {
  name: string;
  label: string;
  value: SelectOption[];
  options: SelectOption[];
  register: UseFormRegister<FieldValues>;
  config?: RegisterOptions<FieldValues, string> | undefined;
  setValue: UseFormSetValue<FieldValues>;
  error?: FormFieldError;
}

export const OpsMultiSelectRegister = (props: Props) => {
  const { name, value, register, setValue, config, options, label, error } =
    props;
  const multiSelectRegister = register(name, {
    value: value ?? "",
    ...config,
  });

  const [selectedOptions, setSelectedOptions] = useState<SelectOption[]>(value);

  return (
    <OpsMultiSelect
      error={error}
      label={label}
      options={options}
      value={selectedOptions}
      onChange={(newValue) => {
        setSelectedOptions(newValue as SelectOption[]);
        setValue(multiSelectRegister.name, newValue);
      }}
    />
  );
};
