import { FieldValues, RegisterOptions, UseFormRegister, UseFormSetValue } from "react-hook-form";
import { FormFieldError } from "../../screens/edit-form-hook/form";
import { SelectOption } from "../inputs/select";
import { OpsSelect } from "./select";

type SelectRegisterProps = {
  name: string;
  value: string;
  label: string;
  options: SelectOption[];
  register: UseFormRegister<FieldValues>;
  config?: RegisterOptions<FieldValues, string> | undefined;
  setValue: UseFormSetValue<FieldValues>;
  error?: FormFieldError;
  isProtected?: boolean;
  isOptional?: boolean;
  disabled?: boolean;
  dropdown?: boolean;
  enum?: boolean;
};

export const OpsSelectRegister = (props: SelectRegisterProps) => {
  const { register, setValue, config, isProtected, disabled, name, ...propsToPass } = props;

  const inputRegister = register(name, {
    value: props.value ?? "",
    ...config,
  });

  return (
    <OpsSelect
      {...propsToPass}
      disabled={!!disabled}
      onChange={(item: SelectOption) => setValue(inputRegister.name, item)}
      isProtected={isProtected || disabled}
    />
  );
};