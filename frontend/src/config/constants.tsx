import { Select2StepPreview } from "../component-preview/select-2-step.preview";
import { BrancheItemDetails } from "../screens/branches/branche-item-details";
import { BranchesItems } from "../screens/branches/branches-items";
import { Diff } from "../screens/branches/diff/diff";
import ObjectItemDetails from "../screens/object-item-details/object-item-details";
import ObjectItems from "../screens/object-items/object-items";
import OpsObjects from "../screens/ops-objects/ops-objects";

export const MAIN_ROUTES = [
  {
    path: "/objects/:objectname/:objectid",
    element: <ObjectItemDetails />,
  },
  {
    path: "/objects/:objectname",
    element: <ObjectItems />,
  },
  {
    path: "/schema",
    element: <OpsObjects />,
  },
  {
    path: "/branches",
    element: <BranchesItems />,
  },
  {
    path: "/branches/:branchname",
    element: <BrancheItemDetails />,
  },
  {
    path: "/branches/:branchname/pull-request",
    element: <Diff />,
  },
];

export const CUSTOM_COMPONENT_ROUTES = [
  {
    path: "/custom-components/select-2-step",
    element: <Select2StepPreview />,
  },
];

export const ADMIN_MENU_ITEMS = [
  {
    path: "/schema",
    label: "Schema"
  }
];

export const BRANCHES_MENU_ITEMS = [
  {
    path: "/branches",
    label: "List"
  },
  {
    path: "/pull-requests",
    label: "Pull requests"
  }
];

export const DEFAULT_BRANCH_NAME = "main";