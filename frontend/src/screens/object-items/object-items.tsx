import { useAtom } from "jotai";
import { gql } from "@apollo/client";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { graphQLClient } from "../..";
import { schemaState } from "../../state/atoms/schema.atom";
import ErrorScreen from "../error-screen/error-screen";
import LoadingScreen from "../loading-screen/loading-screen";
import DeviceFilters from "../device-list/device-filters";
import DeviceFilterBar from "../device-list/device-filter-bar";
import { classNames } from "../../App";

declare var Handlebars: any;

const template = Handlebars.compile(`query {{kind.value}} {
        {{name.value}} {
            {{#each attributes}}
            {{this.name.value}} {
                value
            }
            {{/each}}
        }
    }
`);

export default function ObjectItems() {
  let { objectname } = useParams();
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [objectRows, setObjectRows] = useState([]);
  const [schemaList] = useAtom(schemaState);
  const schema = schemaList.filter((s) => s.name.value === objectname)[0];

  useEffect(() => {
    if (schema) {
      const queryString = template(schema);
      const query = gql`
        ${queryString}
      `;
      const request = graphQLClient.request(query);
      request
        .then((data) => {
          const rows = data[schema.name.value!];
          setObjectRows(rows);
          setIsLoading(false);
        })
        .catch(() => {
          setHasError(true);
        });
    }
  }, [objectname, schemaList, schema]);


  if (hasError) {
    return <ErrorScreen />;
  }

  if (isLoading) {
    return <LoadingScreen />;
  }

  let columns: string[] = [];

  if (objectRows.length) {
    const firstRow = objectRows[0];
    columns = Object.keys(firstRow);
  }

  return (
    <div className="flex-1 overflow-auto pt-0 px-4 sm:px-0 md:px-0">
      <div className="sm:flex sm:items-center pb-4 px-4 sm:px-6 lg:px-8">
        <div className="sm:flex-auto pt-6">
          <h1 className="text-xl font-semibold text-gray-900">
            {schema.kind.value}
          </h1>
          <p className="mt-2 text-sm text-gray-700">
            A list of all the {schema.kind.value} in your infrastructure.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <DeviceFilters />
        </div>
      </div>
      <DeviceFilterBar />
      <div className="mt-0 flex flex-col px-4 sm:px-6 lg:px-8">
        <div className="-my-2 -mx-4 sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full pt-2 align-middle">
            <div className="shadow-sm ring-1 ring-black ring-opacity-5">
              <table
                className="min-w-full border-separate"
                style={{ borderSpacing: 0 }}
              >
                <thead className="bg-gray-50">
                  <tr>
                    {columns.map((column) => (
                      <th
                        scope="col"
                        className="sticky top-0 border-b border-gray-300 bg-gray-50 bg-opacity-75 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 backdrop-blur backdrop-filter sm:pl-6 lg:pl-8"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white">
                  {objectRows.map((row, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      {columns.map((column) => (
                        <td
                          className={classNames(
                            index !== objectRows.length - 1
                              ? "border-b border-gray-200"
                              : "",
                            "whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6 lg:pl-8 uppercase"
                          )}
                        >
                          {(row[column] as any)?.value}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
