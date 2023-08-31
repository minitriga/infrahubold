import { gql, useReactiveVar } from "@apollo/client";
import { PlusIcon, Square3Stack3DIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAtom } from "jotai";
import { useContext, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";
import { ALERT_TYPES, Alert } from "../../components/alert";
import { BUTTON_TYPES, Button } from "../../components/button";
import ModalDelete from "../../components/modal-delete";
import { Pagination } from "../../components/pagination";
import { RoundedButton } from "../../components/rounded-button";
import SlideOver from "../../components/slide-over";
import { DEFAULT_BRANCH_NAME, MENU_EXCLUDELIST } from "../../config/constants";
import { AuthContext } from "../../decorators/withAuth";
import graphqlClient from "../../graphql/graphqlClientApollo";
import { deleteObject } from "../../graphql/mutations/objects/deleteObject";
import { getObjectItemsPaginated } from "../../graphql/queries/objects/getObjectItems";
import { branchVar } from "../../graphql/variables/branchVar";
import { dateVar } from "../../graphql/variables/dateVar";
import useFilters from "../../hooks/useFilters";
import usePagination from "../../hooks/usePagination";
import useQuery from "../../hooks/useQuery";
import { iComboBoxFilter } from "../../state/atoms/filters.atom";
import { genericsState, schemaState } from "../../state/atoms/schema.atom";
import { schemaKindNameState } from "../../state/atoms/schemaKindName.atom";
import { classNames } from "../../utils/common";
import { constructPath } from "../../utils/fetch";
import { getObjectItemDisplayValue } from "../../utils/getObjectItemDisplayValue";
import {
  getSchemaObjectColumns,
  getSchemaRelationshipColumns,
} from "../../utils/getSchemaObjectColumns";
import { getObjectDetailsUrl } from "../../utils/objects";
import { stringifyWithoutQuotes } from "../../utils/string";
import DeviceFilterBar from "../device-list/device-filter-bar-paginated";
import ErrorScreen from "../error-screen/error-screen";
import LoadingScreen from "../loading-screen/loading-screen";
import NoDataFound from "../no-data-found/no-data-found";
import ObjectItemCreate from "../object-item-create/object-item-create-paginated";

export default function ObjectItems(props: any) {
  const { objectname: objectnameFromParams } = useParams();

  const { objectname: objectnameFromProps = "", filters: filtersFromProps = [] } = props;

  const objectname = objectnameFromProps || objectnameFromParams;

  const auth = useContext(AuthContext);

  const [schemaKindName] = useAtom(schemaKindNameState);
  const [schemaList] = useAtom(schemaState);
  const [genericList] = useAtom(genericsState);
  const branch = useReactiveVar(branchVar);
  const date = useReactiveVar(dateVar);
  const [filters] = useFilters();
  const [pagination] = usePagination();
  const [showCreateDrawer, setShowCreateDrawer] = useState(false);
  const [rowToDelete, setRowToDelete] = useState<any>();
  const [deleteModal, setDeleteModal] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const navigate = useNavigate();

  const schema = schemaList.filter((s) => s.name === objectname)[0];
  const generic = genericList.filter((s) => s.name === objectname)[0];

  const schemaData = schema || generic;

  if ((schemaList?.length || genericList?.length) && !schemaData) {
    // If there is no schema nor generics, go to home page
    navigate("/");
  }

  if (schemaData && MENU_EXCLUDELIST.includes(schemaData.kind)) {
    navigate("/");
  }

  // All the fiter values are being sent out as strings inside quotes.
  // This will not work if the type of filter value is not string.
  const filtersString = [
    // Add object filters
    ...filters.map((row: iComboBoxFilter) => `${row.name}: "${row.value}"`),
    // Add pagination filters
    ...[
      { name: "offset", value: pagination?.offset },
      { name: "limit", value: pagination?.limit },
    ].map((row: any) => `${row.name}: ${row.value}`),
    ...filtersFromProps,
  ].join(",");

  // Get all the needed columns (attributes + relationships)
  const columns = getSchemaObjectColumns(schemaData);

  const queryString = schemaData
    ? getObjectItemsPaginated({
        kind: schemaData.kind,
        attributes: schemaData.attributes,
        relationships: getSchemaRelationshipColumns(schemaData),
        filters: filtersString,
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

  const handleDeleteObject = async () => {
    if (!rowToDelete?.id) {
      return;
    }

    setIsLoading(true);

    const mutationString = deleteObject({
      kind: schemaData.kind,
      data: stringifyWithoutQuotes({
        id: rowToDelete?.id,
      }),
    });

    const mutation = gql`
      ${mutationString}
    `;

    await graphqlClient.mutate({
      mutation,
      context: { branch: branch?.name, date },
    });

    refetch();

    setDeleteModal(false);

    setIsLoading(false);

    setRowToDelete(undefined);

    toast(
      <Alert type={ALERT_TYPES.SUCCESS} message={`Object ${rowToDelete?.display_label} deleted`} />
    );
  };

  if (error) {
    console.log("Error while loading objects list: ", error);
    return <ErrorScreen />;
  }

  return (
    <div className="bg-custom-white flex-1 overflow-x-auto flex flex-col">
      <div className="sm:flex sm:items-center py-4 px-4 sm:px-6 lg:px-8 w-full">
        {schemaData && (
          <div className="sm:flex-auto flex items-center">
            <h1 className="text-xl font-semibold text-gray-900">
              {schemaData.name} ({count})
            </h1>
            <p className="mt-2 text-sm text-gray-700 m-0 pl-2 mb-1">
              A list of all the {schemaData.kind} in your infrastructure.
            </p>
          </div>
        )}

        <RoundedButton
          disabled={!auth?.permissions?.write}
          onClick={() => setShowCreateDrawer(true)}>
          <PlusIcon className="h-5 w-5" aria-hidden="true" />
        </RoundedButton>
      </div>

      {schemaData?.filters && <DeviceFilterBar objectname={objectname} />}

      {loading && !rows && <LoadingScreen />}

      {!loading && rows && (
        <div className="mt-0 flex flex-col px-4 sm:px-6 lg:px-8 w-full overflow-x-auto flex-1">
          <div className="-my-2 -mx-4 sm:-mx-6 lg:-mx-8">
            <div className="inline-block min-w-full pt-2 align-middle">
              <div className="shadow-sm ring-1 ring-custom-black ring-opacity-5">
                <table className="min-w-full border-separate" style={{ borderSpacing: 0 }}>
                  <thead className="bg-gray-50">
                    <tr>
                      {columns?.map((attribute) => (
                        <th
                          key={attribute.name}
                          scope="col"
                          className="sticky top-0 border-b border-gray-300 bg-gray-50 bg-opacity-75 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 backdrop-blur backdrop-filter sm:pl-6 lg:pl-8">
                          {attribute.label}
                        </th>
                      ))}
                      <th
                        scope="col"
                        className="sticky top-0 border-b border-gray-300 bg-gray-50 bg-opacity-75 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 backdrop-blur backdrop-filter sm:pl-6 lg:pl-8"></th>
                    </tr>
                  </thead>
                  <tbody className="bg-custom-white">
                    {rows?.map((row: any, index: number) => (
                      <tr
                        onClick={() =>
                          navigate(
                            constructPath(
                              getObjectDetailsUrl(row.id, row.__typename, schemaKindName)
                            )
                          )
                        }
                        key={index}
                        className="hover:bg-gray-50 cursor-pointer">
                        {columns?.map((attribute) => (
                          <td
                            key={row.id + "-" + attribute.name}
                            className={classNames(
                              index !== rows.length - 1 ? "border-b border-gray-200" : "",
                              "whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6 lg:pl-8"
                            )}>
                            {getObjectItemDisplayValue(row, attribute)}
                          </td>
                        ))}

                        <td
                          className={classNames(
                            index !== rows.length - 1 ? "border-b border-gray-200" : "",
                            "whitespace-nowrap py-3 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6 lg:pl-8 flex items-center justify-end"
                          )}>
                          <Button
                            disabled={!auth?.permissions?.write}
                            buttonType={BUTTON_TYPES.INVISIBLE}
                            onClick={() => {
                              setRowToDelete(row);
                              setDeleteModal(true);
                            }}>
                            <TrashIcon className="w-6 h-6 text-red-500" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {!rows?.length && <NoDataFound />}

                <Pagination count={count} />
              </div>
            </div>
          </div>
        </div>
      )}

      <SlideOver
        title={
          <div className="space-y-2">
            <div className="flex items-center w-full">
              <span className="text-lg font-semibold mr-3">Create {objectname}</span>
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
          onCreate={() => setShowCreateDrawer(false)}
          onCancel={() => setShowCreateDrawer(false)}
          objectname={objectname!}
          refetch={refetch}
        />
      </SlideOver>

      <ModalDelete
        title="Delete"
        description={
          <>
            Are you sure you want to remove the object <br /> <b>`{rowToDelete?.display_label}`</b>?
          </>
        }
        onCancel={() => setDeleteModal(false)}
        onDelete={handleDeleteObject}
        open={!!deleteModal}
        setOpen={() => setDeleteModal(false)}
        isLoading={isLoading}
      />
    </div>
  );
}
