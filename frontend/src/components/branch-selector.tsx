import { CheckIcon } from "@heroicons/react/20/solid";
import { CircleStackIcon, PlusIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";
import { formatDistanceToNow } from "date-fns";
import { useAtom } from "jotai";
import { useSearchParams } from "react-router-dom";
import { graphQLClient } from "..";
import { CONFIG } from "../config/config";
import { Branch } from "../generated/graphql";
import { ControlType } from "../screens/edit-form-hook/dynamic-control-types";
import EditFormHookComponent from "../screens/edit-form-hook/edit-form-hook-component";
import { branchState } from "../state/atoms/branch.atom";
import { branchesState } from "../state/atoms/branches.atom";
import { timeState } from "../state/atoms/time.atom";
import { classNames } from "../utils/common";
import { PopOver } from "./popover";
import { RoundedButton } from "./rounded-button";
import { SelectButton } from "./select-button";

export default function BranchSelector() {
  const [branch, setBranch] = useAtom(branchState);
  const [branches] = useAtom(branchesState);
  const [searchParams, setSearchParams] = useSearchParams();

  const [date] = useAtom(timeState);

  const valueLabel = (
    <>
      <CheckIcon className="h-5 w-5" aria-hidden="true" />
      <p className="ml-2.5 text-sm font-medium">
        {
          branch
            ? branch?.name
            : branches.filter((b) => b.is_default)[0]?.name
        }
      </p>
    </>
  );

  const PopOverButton = (
    <RoundedButton className="ml-2 bg-blue-500 text-sm hover:bg-blue-600 focus:ring-blue-500 focus:ring-offset-gray-50 focus:ring-offset-2">
      <PlusIcon
        className="h-5 w-5 text-white"
        aria-hidden="true"
      />
    </RoundedButton>
  );

  const branchesOptions = branches.map(
    (branch) => ({
      value: branch.name,
      label: branch.name
    })
  );

  /**
   * Update GraphQL client endpoint whenever branch changes
   */
  const onBranchChange = (branch: Branch) => {
    graphQLClient.setEndpoint(CONFIG.GRAPHQL_URL(branch?.name, date));

    setBranch(branch);

    if (branch?.is_default) {
      searchParams.delete("branch");
      return setSearchParams(searchParams);
    }

    return setSearchParams({
      branch: branch?.name
    });
  };

  const renderOption = ({ option, active, selected }: any) => (
    <div className="flex relative flex-col">
      {
        option.is_data_only
        && (
          <div className="absolute bottom-0 right-0">
            <CircleStackIcon
              className={classNames(
                "h-4 w-4",
                active ? "text-white" : "text-gray-500"
              )}
            />
          </div>
        )
      }

      {
        option.is_default
        && (
          <div className="absolute bottom-0 right-0">
            <ShieldCheckIcon
              className={classNames(
                "h-4 w-4",
                active ? "text-white" : "text-gray-500"
              )}
            />
          </div>
        )
      }

      <div className="flex justify-between">
        <p
          className={
            selected ? "font-semibold" : "font-normal"
          }
        >
          {option.name}
        </p>
        {
          selected
            ? (
              <span
                className={
                  active ? "text-white" : "text-blue-500"
                }
              >
                <CheckIcon
                  className="h-5 w-5"
                  aria-hidden="true"
                />
              </span>
            )
            : null
        }
      </div>
      {
        option?.created_at
        && (
          <p
            className={classNames(
              active ? "text-blue-200" : "text-gray-500",
              "mt-2"
            )}
          >
            {formatDistanceToNow(
              new Date(option?.created_at),
              { addSuffix: true }
            )}
          </p>
        )
      }
    </div>
  );

  const handleSubmit = async (data: any) => {
    console.log("data: ", data);
    return;
    // try {
    //   await createBranch({
    //     name: newBranchName,
    //     description: newBranchDescription,
    //     // origin_branch: originBranch ?? branches[0]?.name,
    //     // branched_from: formatISO(branchedFrom ?? new Date()),
    //     is_data_only: isDataOnly
    //   });

    //   toast(<Alert type={ALERT_TYPES.SUCCESS} message={"Branch created"} />);
    // } catch (e) {
    //   const details = "An error occured while creating the branch";
    //   toast(<Alert type={ALERT_TYPES.ERROR} message={"An error occured"} details={details} />);
    // }
  };

  /**
   * There's always a main branch present at least.
   */
  if (!branches.length) {
    return null;
  }

  const formStructure = [
    {
      fieldName: "name",
      type: "String",
      inputType: "text" as ControlType,
      label: "Branch name",
      defaultValue: "",
      isAttribute: false,
      isRelationship: false,
      options: {
        values: []
      }
    },
    {
      fieldName: "description",
      type: "String",
      inputType: "text" as ControlType,
      label: "Description",
      defaultValue: "",
      isAttribute: false,
      isRelationship: false,
      options: {
        values: []
      }
    },
    {
      fieldName: "origin_branch",
      type: "String",
      inputType: "select" as ControlType,
      label: "Branch name",
      defaultValue: "",
      isAttribute: false,
      isRelationship: false,
      options: {
        values: branchesOptions
      },
      disabled: true
    },
    {
      fieldName: "branched_from",
      type: "String",
      inputType: "text" as ControlType,
      label: "Branched from",
      defaultValue: "",
      isAttribute: false,
      isRelationship: false,
      options: {
        values: []
      },
      disabled: true
    },
    {
      fieldName: "is_data_only",
      type: "String",
      inputType: "checkbox" as ControlType,
      label: "Is data only",
      defaultValue: true,
      isAttribute: false,
      isRelationship: false,
      options: {
        values: []
      },
    },
  ];

  return (
    <>
      <SelectButton
        value={branch ? branch : branches.filter((b) => b.is_default)[0]}
        valueLabel={valueLabel}
        onChange={onBranchChange}
        options={branches}
        renderOption={renderOption}
      />
      <PopOver buttonComponent={PopOverButton} className="right-0" title={"Create a new branch"}>
        <EditFormHookComponent onSubmit={handleSubmit} fields={formStructure} />

        {/* Branch name:
          <Input value={newBranchName} onChange={setNewBranchName} />

          Branch description:
          <Input value={newBranchDescription} onChange={setNewBranchDescription} />

          Branched from:
          <Select disabled options={branchesOptions} value={originBranch ?? defaultBranch} onChange={handleBranchedFrom} />

          Branched at:
          <Input value={format(branchedFrom ?? new Date(), "MM/dd/yyy HH:mm")} onChange={setNewBranchName} disabled />

          Is data only:
          <Switch enabled={isDataOnly} onChange={setIsDataOnly} /> */}
      </PopOver>
    </>
  );
}
