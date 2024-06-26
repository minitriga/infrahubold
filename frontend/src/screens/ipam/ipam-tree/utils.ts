import { TreeItemProps, TreeProps } from "../../../components/ui/tree";
import { IP_PREFIX_GENERIC, IPAM_TREE_ROOT_ID } from "../constants";

export type PrefixNode = {
  id: string;
  display_label: string;
  parent: {
    node: {
      id: string;
      display_label: string;
    } | null;
  };
  children: {
    count: number;
  };
  __typename: string;
};

export type AncestorNode = {
  id: string;
  display_label: string;
  ancestors: { edges: Array<{ node: Omit<PrefixNode, "children"> }> };
};

export type PrefixData = {
  BuiltinIPPrefix: {
    edges: Array<{ node: PrefixNode }>;
  };
};
export type AncestorsData = {
  BuiltinIPPrefix: {
    edges: Array<{ node: AncestorNode }>;
  };
};

export const ROOT_TREE_ITEM: TreeItemProps["element"] = {
  id: IPAM_TREE_ROOT_ID,
  name: "",
  parent: null,
  children: [],
  isBranch: true,
};

export const EMPTY_IPAM_TREE: TreeProps["data"] = [ROOT_TREE_ITEM];

export const formatIPPrefixResponseForTreeView = (data: PrefixData): TreeItemProps["element"][] => {
  const prefixes = data[IP_PREFIX_GENERIC].edges.map(({ node }) => ({
    id: node.id,
    name: node.display_label,
    parent: node.parent.node?.id ?? IPAM_TREE_ROOT_ID,
    children: [],
    isBranch: node.children.count > 0,
    metadata: {
      kind: node.__typename,
    },
  }));

  return prefixes;
};

export const updateTreeData = (
  list: TreeProps["data"],
  id: string,
  children: TreeProps["data"]
) => {
  const data = list.map((node) => {
    if (node.id === id) {
      node.children = children.map((el) => {
        return el.id;
      });
    }
    return node;
  });
  return [...data, ...children];
};

export const getTreeItemAncestors = (
  tree: TreeProps["data"],
  treeItemId: TreeProps["data"][0]["id"]
): TreeProps["data"] => {
  const currentTreeItem = tree.find(({ id }) => id === treeItemId);
  if (!currentTreeItem || currentTreeItem.parent === null) return [];

  const parent = tree.find(({ id }) => id === currentTreeItem.parent);
  if (!parent) return [];

  return [parent, ...getTreeItemAncestors(tree, parent.id)];
};
