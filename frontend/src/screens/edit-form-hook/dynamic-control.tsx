import { useAtom } from "jotai";
import { useCallback, useEffect, useState } from "react";
import { useFormContext } from "react-hook-form";
import { schemaState } from "../../state/atoms/schema.atom";
import getDropdownOptionsForRelatedPeers, { iPeerDropdownOption } from "../../utils/dropdownOptionsForRelatedPeers";
import { ControlType, DynamicFieldData, RelationshipCardinality, SelectOption } from "./dynamic-control-types";
import MultiSelect from "./multi-select";

const getNestedFieldName = (fieldName: string, isAttribute: boolean, isRelationship: boolean, relationshipCardinality?: RelationshipCardinality): string => {
  if(isAttribute) {
    return fieldName + ".value";
  } else if (isRelationship && relationshipCardinality === "one") {
    return fieldName + ".id";
  } else {
    return fieldName + ".list";
  }
};

export const DynamicControl = (props: DynamicFieldData) => {
  const {
    inputType,
    fieldName,
    type,
    defaultValue,
    isAttribute,
    isRelationship,
    relationshipCardinality,
    options = {
      values: [],
    },
    config = {},
  } = props;
  const { register, control } = useFormContext();

  const name = getNestedFieldName(fieldName, isAttribute, isRelationship, relationshipCardinality);

  let value: any;
  if(!defaultValue) {
    value = "";
  } else {
    if(isAttribute) {
      value = defaultValue.value;
    } else if(relationshipCardinality === "many") {
      value = defaultValue.map((item: any) => item.id);
    } else {
      value = defaultValue.id;
    }
  }

  const getFormFieldByInputType = (inputType: ControlType) => {
    switch (inputType) {
      case "text":
        return (
          <input
            className="mt-2 block w-full max-w-lg rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
            type="text"
            {...register(name, config)}
            defaultValue={value}
          />
        );
      case "select": {
        let selectConfig = {};
        if(type === "Integer") {
          selectConfig = {
            valueAsNumber: true,
          };
        }
        return (
          <select
            className="mt-2 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
            {...register(name, {
              ...config,
              ...selectConfig,
            })}
            defaultValue={value}
            name={name}
            id={name}
          >
            {options.values.map((o, index) => (
              <option key={index} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        );
      }
      case "multiselect": {
        const def = options.values.filter(
          (option) => (value || []).indexOf(option.value) > -1
        );
        const field = register(name, {
          ...config,
          value: def,
        });
        // If user does not change anything in the multi-select dropdown, the field value in the form data remains undefined
        // Not a problem currently, as if nothing get's changed, we are not sending out that field in the update mutation
        // but something that we can look into later on
        return (
          <MultiSelect
            {...props}
            fieldName={name}
            options={options.values}
            control={control}
            onChange={field.onChange}
          />
        );
      }
      case "number":
        return (
          <input
            className="mt-2 block w-full max-w-lg rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
            type="number"
            {...register(name, {
              valueAsNumber: true,
            })}
            defaultValue={value}
          />
        );
      case "checkbox":
        return <input
          type="checkbox"
          {...register(name)}
          defaultValue={value}
        />;
      default:
        return <input type="text" />;
    }
  };

  return getFormFieldByInputType(inputType);
};

interface iSourceOwnerFieldProps {
  field: DynamicFieldData;
  metaFieldName: string;
}

export const SourceOwnerField = (props: iSourceOwnerFieldProps) => {
  const {
    field,
    metaFieldName,
  } = props;
  const { register } = useFormContext();
  const [schemaList] = useAtom(schemaState);

  const relatedObjects: { [key: string]: string; } = {
    "source": "DataSource",
    "owner": "DataOwner",
    "_relation__source": "DataSource",
    "_relation__owner": "DataOwner",
  };

  const schemaOptions: SelectOption[] = [{
    label: "",
    value: "",
  }, ...schemaList.filter(schema => {
    if((schema.inherit_from || []).indexOf(relatedObjects[metaFieldName]) > -1) {
      return true;
    } else {
      return false;
    }
  }).map(schema => ({
    label: schema.kind,
    value: schema.name,
  }))];

  const [relatedItemOptions, setRelatedItemOptions] = useState<iPeerDropdownOption[]>([]);

  const name = field.fieldName + "." + metaFieldName;
  const metaFieldObject = field.defaultValue[metaFieldName];

  const [objectKindname, setObjectKindName] = useState(metaFieldObject ? metaFieldObject.__typename : "");

  const setDropdownOptions = useCallback(async () => {
    const schema = schemaList.filter(schema => schema.kind === objectKindname);
    if(schema.length) {
      const objectName = schema[0].name;
      const peerDropdownOptions = await getDropdownOptionsForRelatedPeers([objectName]);
      const options = peerDropdownOptions[objectName];
      setRelatedItemOptions(options);
    }
  }, [objectKindname, schemaList]);

  useEffect(() => {
    setDropdownOptions();
  }, [objectKindname, setDropdownOptions]);

  return <>
    <div className="sm:col-span-1"></div>
    <div className="sm:col-span-6">
      <label
        className="block text-sm font-medium leading-6 text-gray-900 capitalize mt-4 mb-2">
        {metaFieldName.split("_").filter(r => !!r).join(" ")}
      </label>
    </div>
    <div className="sm:col-span-1"></div>
    <div className="sm:col-span-3">
      <select
        className="block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
        defaultValue={objectKindname}
        placeholder="Choose Type"
        onChange={(e) => setObjectKindName(e.target.value)}
      >
        {schemaOptions.map((o, index) => (
          <option key={index} value={o.label}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
    <div className="sm:col-span-3">
      {relatedItemOptions.length > 0 && <select
        className="block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
        {...register(name, {
          value: metaFieldObject ? metaFieldObject.id : "",
        })}
      >
        {relatedItemOptions.map((o, index) => (
          <option key={index} value={o.id}>
            {o.display_label}
          </option>
        ))}
      </select>}
    </div>

  </>;
};

export const MetaToggleField = (props: iSourceOwnerFieldProps) => {
  const {
    field,
    metaFieldName,
  } = props;
  const { register } = useFormContext();

  const name = field.fieldName + "." + metaFieldName;
  const metaFieldValue = field.defaultValue[metaFieldName];

  return <>
    <div className="sm:col-span-1"></div>
    <div className="sm:col-span-6">
      <label
        className="block text-sm font-medium leading-6 text-gray-900 capitalize mt-4 mb-2">
        {metaFieldName.split("_").filter(r => !!r).join(" ")}
      </label>
    </div>
    <div className="sm:col-span-1"></div>
    <div className="sm:col-span-6">
      <input type="checkbox" {...register(name, {
        value: metaFieldValue,
      })} />
    </div>
  </>;
};

export const MetaDataFields = (props: DynamicFieldData) => {
  const {
    isAttribute,
  } = props;

  const sourceOwnerFields = isAttribute ? ["owner", "source"] : ["_relation__owner", "_relation__source"];
  const booleanFields = isAttribute ? ["is_visible", "is_protected"] : ["_relation__is_visible", "_relation__is_protected"];

  return <>
    {booleanFields.map(field => <MetaToggleField field={props} metaFieldName={field} key={field} />)}
    {sourceOwnerFields.map(sourceOwnerField => <SourceOwnerField field={props} metaFieldName={sourceOwnerField} key={sourceOwnerField} />)}
  </>;
};
