import { Tabs } from "../../../components/tabs";
import { StringParam, useQueryParam } from "use-query-params";
import { DataDiff } from "./data-diff";
import { QSP } from "../../../config/qsp";
import { SchemaDiff } from "./schema-diff";
import { formatISO } from "date-fns/esm";
import { parseISO } from "date-fns";
import { Filters } from "../../../components/filters";
import { DynamicFieldData } from "../../edit-form-hook/dynamic-control-types";

const DIFF_TABS = {
  CONVERSATIONS: "conversation",
  STATUS: "status",
  DATA: "data",
  FILES: "files",
  CHECKS: "checks",
  ARTIFACTS: "artifacts",
  SCHEMA: "schema",
};

const tabs = [
  // {
  //   label: "Conversation",
  //   name: DIFF_TABS.CONVERSATIONS
  // },
  // {
  //   label: "Status",
  //   name: DIFF_TABS.STATUS
  // },
  {
    label: "Data",
    name: DIFF_TABS.DATA,
  },
  {
    label: "Files",
    name: DIFF_TABS.FILES,
  },
  // {
  //   label: "Checks",
  //   name: DIFF_TABS.CHECKS
  // },
  // {
  //   label: "Artifacts",
  //   name: DIFF_TABS.ARTIFACTS
  // },
  {
    label: "Schema",
    name: DIFF_TABS.SCHEMA,
  },
];

const renderContent = (tab: string | null | undefined) => {
  switch (tab) {
    case DIFF_TABS.FILES:
      // return <FilesDiff />;
      return null;
    case DIFF_TABS.SCHEMA:
      return <SchemaDiff />;
    default:
      return <DataDiff />;
  }
};

export const Diff = () => {
  const [qspTab] = useQueryParam(QSP.BRANCH_DIFF_TAB, StringParam);
  const [branchOnly, setBranchOnly] = useQueryParam(
    QSP.BRANCH_FILTER_BRANCH_ONLY,
    StringParam
  );
  const [timeFrom, setTimeFrom] = useQueryParam(
    QSP.BRANCH_FILTER_TIME_FROM,
    StringParam
  );
  const [timeTo, setTimeTo] = useQueryParam(
    QSP.BRANCH_FILTER_TIME_TO,
    StringParam
  );

  const fields: DynamicFieldData[] = [
    {
      name: "branch_only",
      label: "Branch only",
      type: "switch",
      value: branchOnly === "true",
    },
    {
      name: "time_from",
      label: "Time from",
      type: "datepicker",
      value: timeFrom ? parseISO(timeFrom) : undefined,
    },
    {
      name: "time_to",
      label: "Time to",
      type: "datepicker",
      value: timeTo ? parseISO(timeTo) : undefined,
    },
  ];

  const handleSubmit = (data: any) => {
    const { branch_only, time_from, time_to } = data;

    if (branch_only !== undefined) {
      setBranchOnly(branch_only);
    }

    setTimeFrom(time_from ? formatISO(time_from) : undefined);

    setTimeTo(time_to ? formatISO(time_to) : undefined);
  };

  return (
    <div>
      <div className="bg-white p-6 flex">
        <Filters fields={fields} onSubmit={handleSubmit} />
      </div>

      <div>
        <Tabs tabs={tabs} qsp={QSP.BRANCH_DIFF_TAB} />
      </div>

      <div>{renderContent(qspTab)}</div>
    </div>
  );
};
