import { TreeItemProps, Tree, TreeProps } from "../../components/ui/tree";
import { useLazyQuery } from "../../hooks/useQuery";
import React, { useEffect, useState } from "react";
import { ITreeViewOnLoadDataProps } from "react-accessible-treeview";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "@iconify-icon/react";
import { GET_PREFIXES_ONLY } from "../../graphql/queries/ipam/prefixes";
import { useAtomValue } from "jotai/index";
import { genericsState, IModelSchema, schemaState } from "../../state/atoms/schema.atom";
import { constructPathForIpam } from "./common/utils";
import { IpamTreeSkeleton } from "./ipam-tree/ipam-tree-skeleton";
import { IPAM_TREE_ROOT_ID } from "./constants";
import { formatIPPrefixResponseForTreeView, PrefixData, updateTreeData } from "./ipam-tree/utils";

export default function IpamTree({ prefixSchema }: { prefixSchema?: IModelSchema }) {
  const [treeData, setTreeData] = useState<TreeProps["data"]>([
    {
      id: IPAM_TREE_ROOT_ID,
      name: "",
      parent: null,
      children: [],
      isBranch: true,
    },
  ]);
  const [fetchPrefixes] = useLazyQuery<PrefixData, { parentIds: string[] }>(GET_PREFIXES_ONLY);
  const navigate = useNavigate();

  useEffect(() => {
    fetchPrefixes().then(({ data }) => {
      if (!data) return;

      const treeNodes = formatIPPrefixResponseForTreeView(data);

      const rootTreeNodes = treeNodes.filter(({ parent }) => parent === IPAM_TREE_ROOT_ID);

      // assign all prefixes and IP addresses without parent to the root node
      setTreeData((tree) => updateTreeData(tree, IPAM_TREE_ROOT_ID, rootTreeNodes));
    });
  }, []);

  const isLoading = !prefixSchema || treeData.length === 1;

  const onLoadData = async ({ element }: ITreeViewOnLoadDataProps) => {
    if (element.children.length > 0) return; // To avoid refetching data

    const { data } = await fetchPrefixes({
      variables: { parentIds: [element.id.toString()] },
    });

    if (!data) return;

    const treeNodes = formatIPPrefixResponseForTreeView(data);
    setTreeData((tree) => updateTreeData(tree, element.id.toString(), treeNodes));
  };

  return (
    <nav className="min-w-64">
      <h3 className="font-semibold mb-2">Navigation</h3>

      {isLoading ? (
        <IpamTreeSkeleton />
      ) : (
        <Tree
          data={treeData}
          itemContent={IpamTreeItem}
          onLoadData={onLoadData}
          onNodeSelect={({ element, isSelected }) => {
            if (!isSelected) return;

            const url = constructPathForIpam(`/ipam/prefixes/${encodeURIComponent(element.name)}`);
            navigate(url);
          }}
        />
      )}
    </nav>
  );
}

const IpamTreeItem = ({ element }: TreeItemProps) => {
  const nodes = useAtomValue(schemaState);
  const generics = useAtomValue(genericsState);

  const schema = [...nodes, ...generics].find(({ kind }) => kind === element.metadata?.kind);
  const url = constructPathForIpam(`/ipam/prefixes/${encodeURIComponent(element.name)}`);

  return (
    <Link to={url} tabIndex={-1} className="flex items-center gap-2 overflow-hidden">
      {schema?.icon ? <Icon icon={schema.icon as string} /> : <div className="w-4" />}
      <span className="truncate">{element.name}</span>
    </Link>
  );
};
