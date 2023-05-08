import { gql } from "@apollo/client";
import { PlusIcon, Square3Stack3DIcon } from "@heroicons/react/24/outline";

import { useAtom } from "jotai";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { RoundedButton } from "../../components/rounded-button";
import SlideOver from "../../components/slide-over";
import { DEFAULT_BRANCH_NAME } from "../../config/constants";
import { graphQLClient } from "../../graphql/graphqlClient";
import { branchState } from "../../state/atoms/branch.atom";
import { comboxBoxFilterState } from "../../state/atoms/filters.atom";
import { schemaState } from "../../state/atoms/schema.atom";
import { timeState } from "../../state/atoms/time.atom";
import { classNames } from "../../utils/common";
import { constructPath } from "../../utils/fetch";
import { getObjectItemDisplayValue } from "../../utils/getObjectItemDisplayValue";
import {
  getSchemaObjectColumns,
  getSchemaRelationshipColumns,
} from "../../utils/getSchemaObjectColumns";
import { getObjectUrl } from "../../utils/objects";
import DeviceFilterBar from "../device-list/device-filter-bar";
import ErrorScreen from "../error-screen/error-screen";
import LoadingScreen from "../loading-screen/loading-screen";
import NoDataFound from "../no-data-found/no-data-found";
import ObjectItemCreate from "../object-item-create/object-item-create";

declare const Handlebars: any;

const template = Handlebars.compile(`query {{kind}} {
        {{name}}{{#if filterString}}({{{filterString}}}){{/if}} {
            id
            display_label
            {{#each attributes}}
              {{this.name}} {
                  value
              }
            {{/each}}
            {{#each relationships}}
              {{this.name}} {
                  display_label
              }
            {{/each}}
        }
    }
`);

export default function ObjectItems() {
  const { objectname } = useParams();
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [objectRows, setObjectRows] = useState<any[] | undefined>();
  const [schemaList] = useAtom(schemaState);
  const [date] = useAtom(timeState);
  const [branch] = useAtom(branchState);
  const schema = schemaList.filter((s) => s.name === objectname)[0];
  const [currentFilters] = useAtom(comboxBoxFilterState);

  const [showCreateDrawer, setShowCreateDrawer] = useState(false);

  // All the fiter values are being sent out as strings inside quotes.
  // This will not work if the type of filter value is not string.
  const filterString = currentFilters
    .map((row) => `${row.name}: "${row.value}"`)
    .join(",");
  // Get all the needed columns (attributes + relationships with a cardinality of "one")
  const columns = getSchemaObjectColumns(schema);

  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    if (schema) {
      try {
        setHasError(false);
        setIsLoading(true);
        setObjectRows(undefined);

        const queryString = template({
          ...schema,
          filterString,
          relationships: getSchemaRelationshipColumns(schema),
        });

        const query = gql`
          ${queryString}
        `;

        const data: any = await graphQLClient.request(query);

        // Get actual param from pathname to get current object
        const params = window.location.pathname.split("/");
        const currentObject = params[params.length - 1];

        // Update state only if the query is for the current object
        // TODO: Update that when switching to new graphql client and cancel query
        if (currentObject === objectname) {
          const rows = data[schema.name];
          setObjectRows(rows);
        }

        setIsLoading(false);
      } catch (e) {
        console.error("Error: ", e);
        setHasError(true);
        setIsLoading(false);
      }
    }
  }, [filterString, schema, objectname]);

  useEffect(() => {
    loadData();
  }, [
    objectname,
    schemaList,
    schema,
    date,
    branch,
    currentFilters,
    filterString,
    loadData,
  ]);

  if (hasError) {
    return <ErrorScreen />;
  }

  return (
    <div className="bg-white flex-1 overflow-x-auto flex flex-col">
      <div className="sm:flex sm:items-center py-4 px-4 sm:px-6 lg:px-8 w-full">
        {schema && (
          <div className="sm:flex-auto flex items-center">
            <h1 className="text-xl font-semibold text-gray-900">
              {schema.kind} ({objectRows?.length})
            </h1>
            <p className="mt-2 text-sm text-gray-700 m-0 pl-2 mb-1">
              A list of all the {schema.kind} in your infrastructure.
            </p>
          </div>
        )}

        <RoundedButton onClick={() => setShowCreateDrawer(true)}>
          <PlusIcon className="h-5 w-5" aria-hidden="true" />
        </RoundedButton>
      </div>

      {schema && <DeviceFilterBar schema={schema} />}

      {isLoading && !objectRows && <LoadingScreen />}

      {!isLoading && objectRows && (
        <div className="mt-0 flex flex-col px-4 sm:px-6 lg:px-8 w-full overflow-x-auto flex-1">
          <div className="-my-2 -mx-4 sm:-mx-6 lg:-mx-8">
            <div className="inline-block min-w-full pt-2 align-middle">
              <div className="shadow-sm ring-1 ring-black ring-opacity-5">
                <table
                  className="min-w-full border-separate"
                  style={{ borderSpacing: 0 }}
                >
                  <thead className="bg-gray-50">
                    <tr>
                      {columns?.map((attribute) => (
                        <th
                          key={attribute.name}
                          scope="col"
                          className="sticky top-0 border-b border-gray-300 bg-gray-50 bg-opacity-75 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 backdrop-blur backdrop-filter sm:pl-6 lg:pl-8"
                        >
                          {attribute.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white">
                    {objectRows?.map((row, index) => (
                      <tr
                        onClick={() =>
                          navigate(
                            constructPath(
                              getObjectUrl({ kind: schema.name, id: row.id })
                            )
                          )
                        }
                        key={index}
                        className="hover:bg-gray-50 cursor-pointer"
                      >
                        {columns?.map((attribute) => (
                          <td
                            key={row.id + "-" + attribute.name}
                            className={classNames(
                              index !== objectRows.length - 1
                                ? "border-b border-gray-200"
                                : "",
                              "whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6 lg:pl-8"
                            )}
                          >
                            {getObjectItemDisplayValue(row, attribute)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>

                {!objectRows?.length && <NoDataFound />}
              </div>
            </div>
          </div>
        </div>
      )}
      {
        <SlideOver
          title={
            <div className="space-y-2">
              <div className="flex items-center w-full">
                <span className="text-lg font-semibold mr-3">
                  Create {objectname}
                </span>
                <div className="flex-1"></div>
                <div className="flex items-center">
                  <Square3Stack3DIcon className="w-5 h-5" />
                  <div className="ml-1.5 pb-1">
                    {branch?.name ?? DEFAULT_BRANCH_NAME}
                  </div>
                </div>
              </div>
              <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20">
                <svg
                  className="h-1.5 w-1.5 mr-1 fill-yellow-500"
                  viewBox="0 0 6 6"
                  aria-hidden="true"
                >
                  <circle cx={3} cy={3} r={3} />
                </svg>
                {schema?.kind}
              </span>
            </div>
          }
          open={showCreateDrawer}
          setOpen={setShowCreateDrawer}
          // title={`Create ${objectname}`}
        >
          <ObjectItemCreate
            onCreate={() => {
              setShowCreateDrawer(false);
              loadData();
            }}
            onCancel={() => setShowCreateDrawer(false)}
            objectname={objectname!}
          />
        </SlideOver>
      }
    </div>
  );
}
