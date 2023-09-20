import { gql, useReactiveVar } from "@apollo/client";
import { PlusIcon, Square3Stack3DIcon } from "@heroicons/react/24/outline";
import { useAtom } from "jotai";
import { useContext, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RoundedButton } from "../../components/rounded-button";
import SlideOver from "../../components/slide-over";
import { ACCOUNT_OBJECT, DEFAULT_BRANCH_NAME, PROPOSED_CHANGES } from "../../config/constants";
import { AuthContext } from "../../decorators/withAuth";
import { getProposedChanges } from "../../graphql/queries/proposed-changes/getProposedChanges";
import { branchVar } from "../../graphql/variables/branchVar";
import useQuery from "../../hooks/useQuery";
import { branchesState } from "../../state/atoms/branches.atom";
import { schemaState } from "../../state/atoms/schema.atom";
import { constructPath } from "../../utils/fetch";
import { getSchemaRelationshipColumns } from "../../utils/getSchemaObjectColumns";
import ErrorScreen from "../error-screen/error-screen";
import LoadingScreen from "../loading-screen/loading-screen";
import ObjectItemCreate from "../object-item-create/object-item-create-paginated";
import { getFormStructure } from "./conversations";
import { ProposedChange } from "./proposed-changes-item";

export const ProposedChanges = () => {
  const [schemaList] = useAtom(schemaState);
  const [branches] = useAtom(branchesState);
  const auth = useContext(AuthContext);
  const branch = useReactiveVar(branchVar);
  const navigate = useNavigate();
  const [showCreateDrawer, setShowCreateDrawer] = useState(false);

  const schemaData = schemaList.filter((s) => s.name === PROPOSED_CHANGES)[0];
  const accountSchemaData = schemaList.filter((s) => s.name === ACCOUNT_OBJECT)[0];

  const queryString = schemaData
    ? getProposedChanges({
        kind: schemaData.kind,
        accountKind: accountSchemaData.kind,
        attributes: schemaData.attributes,
        relationships: getSchemaRelationshipColumns(schemaData),
      })
    : // Empty query to make the gql parsing work
      // TODO: Find another solution for queries while loading schemaData
      "query { ok }";

  const query = gql`
    ${queryString}
  `;

  const { loading, error, data = {}, refetch } = useQuery(query, { skip: !schemaData });

  const result = data ? data[schemaData?.kind] ?? {} : {};

  const { count, edges } = result;

  const rows = edges?.map((edge: any) => edge.node);

  const customObject = {
    created_by: {
      id: auth?.data?.sub,
    },
  };

  if (!schemaData || loading) {
    return <LoadingScreen />;
  }

  if (error) {
    return <ErrorScreen message="Something went wrong when fetching the proposed changes list." />;
  }

  const branchesOptions: any[] = branches
    .filter((branch) => branch.name !== "main")
    .map((branch) => ({ id: branch.name, name: branch.name }));

  const reviewersOptions: any[] = data
    ? data[accountSchemaData.kind]?.edges.map((edge: any) => ({
        id: edge?.node.id,
        name: edge?.node?.display_label,
      }))
    : [];

  const formStructure = getFormStructure(branchesOptions, reviewersOptions);

  return (
    <div>
      <div className="bg-white sm:flex sm:items-center py-4 px-4 sm:px-6 lg:px-8 w-full">
        {schemaData && (
          <div className="sm:flex-auto flex items-center">
            <h1 className="text-xl font-semibold text-gray-900">
              {schemaData.name} ({count})
            </h1>
          </div>
        )}

        <RoundedButton
          disabled={!auth?.permissions?.write}
          onClick={() => setShowCreateDrawer(true)}>
          <PlusIcon className="h-5 w-5" aria-hidden="true" />
        </RoundedButton>
      </div>

      <ul className="grid gap-6 grid-cols-1 p-6">
        {rows.map((row: any, index: number) => (
          <ProposedChange key={index} row={row} refetch={refetch} />
        ))}
      </ul>

      <SlideOver
        title={
          <div className="space-y-2">
            <div className="flex items-center w-full">
              <span className="text-lg font-semibold mr-3">Create {PROPOSED_CHANGES}</span>
              <div className="flex-1"></div>
              <div className="flex items-center">
                <Square3Stack3DIcon className="w-5 h-5" />
                <div className="ml-1.5 pb-1">{branch?.name ?? DEFAULT_BRANCH_NAME}</div>
              </div>
            </div>
            <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20">
              <svg
                className="h-1.5 w-1.5 mr-1 fill-yellow-500"
                viewBox="0 0 6 6"
                aria-hidden="true">
                <circle cx={3} cy={3} r={3} />
              </svg>
              {schemaData?.kind}
            </span>
          </div>
        }
        open={showCreateDrawer}
        setOpen={setShowCreateDrawer}
        // title={`Create ${objectname}`}
      >
        <ObjectItemCreate
          onCreate={(response: any) => {
            setShowCreateDrawer(false);
            if (response?.object?.id) {
              const url = constructPath(`/proposed-changes/${response?.object?.id}`);
              navigate(url);
            }
          }}
          onCancel={() => setShowCreateDrawer(false)}
          objectname={PROPOSED_CHANGES!}
          refetch={refetch}
          formStructure={formStructure}
          customObject={customObject}
        />
      </SlideOver>
    </div>
  );
};
