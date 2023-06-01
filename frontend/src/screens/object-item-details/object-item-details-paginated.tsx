import { gql, useReactiveVar } from "@apollo/client";
import { ChevronRightIcon } from "@heroicons/react/20/solid";
import {
  CheckIcon,
  LockClosedIcon,
  PencilIcon,
  PencilSquareIcon,
  Square3Stack3DIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useAtom } from "jotai";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { StringParam, useQueryParam } from "use-query-params";
import { Button } from "../../components/button";
import MetaDetailsTooltip from "../../components/meta-details-tooltips";
import SlideOver from "../../components/slide-over";
import { Tabs } from "../../components/tabs";
import { DEFAULT_BRANCH_NAME } from "../../config/constants";
import { QSP } from "../../config/qsp";
import { getObjectDetailsPaginated } from "../../graphql/queries/objects/getObjectDetails";
import { branchVar } from "../../graphql/variables/branchVar";
import useQuery from "../../hooks/useQuery";
import { showMetaEditState } from "../../state/atoms/metaEditFieldDetails.atom";
import { schemaState } from "../../state/atoms/schema.atom";
import { metaEditFieldDetailsState } from "../../state/atoms/showMetaEdit.atom copy";
import { classNames } from "../../utils/common";
import { constructPath } from "../../utils/fetch";
import {
  getSchemaRelationshipColumns,
  getSchemaRelationshipsTabs,
} from "../../utils/getSchemaObjectColumns";
import ErrorScreen from "../error-screen/error-screen";
import LoadingScreen from "../loading-screen/loading-screen";
import NoDataFound from "../no-data-found/no-data-found";
import ObjectItemEditComponent from "../object-item-edit/object-item-edit-paginated";
import ObjectItemMetaEdit from "../object-item-meta-edit/object-item-meta-edit";
import RelationshipDetails from "./relationship-details-paginated";
import RelationshipsDetails from "./relationships-details-paginated";

export default function ObjectItemDetails() {
  const { objectname, objectid } = useParams();
  const [qspTab] = useQueryParam(QSP.TAB, StringParam);
  const [showEditDrawer, setShowEditDrawer] = useState(false);
  const [showMetaEditModal, setShowMetaEditModal] = useAtom(showMetaEditState);
  const [metaEditFieldDetails, setMetaEditFieldDetails] = useAtom(metaEditFieldDetailsState);
  const [schemaList] = useAtom(schemaState);
  const branch = useReactiveVar(branchVar);
  const schema = schemaList.filter((s) => s.name === objectname)[0];

  const relationships = getSchemaRelationshipColumns(schema);

  const relationshipsTabs = getSchemaRelationshipsTabs(schema);

  const tabs = [
    {
      label: schema?.label,
      name: schema?.label,
    },
    ...relationshipsTabs,
  ];

  const queryString = schema
    ? getObjectDetailsPaginated({
        ...schema,
        relationships,
        objectid,
      })
    : // Empty query to make the gql parsing work
      // TODO: Find another solution for queries while loading schema
      "query { ok }";

  const query = gql`
    ${queryString}
  `;

  const { loading, error, data, refetch } = useQuery(query, { skip: !schema });

  const navigate = useNavigate();

  if (error) {
    console.error("Error while loading the object details: ", error);
    return <ErrorScreen />;
  }

  if (loading || !schema) {
    return <LoadingScreen />;
  }

  if (!data || (data && !data[schema.name] && !data[schema.name]?.edges)) {
    return <NoDataFound />;
  }

  const objectDetailsData = data[schema.name]?.edges[0]?.node;

  if (!objectDetailsData) {
    return null;
  }

  return (
    <div className="bg-white flex-1 overflow-auto flex flex-col">
      <div className="px-4 py-5 sm:px-6 flex items-center">
        <div
          onClick={() => navigate(constructPath(`/objects/${objectname}`))}
          className="text-base font-semibold leading-6 text-gray-900 cursor-pointer hover:underline">
          {schema.kind}
        </div>
        <ChevronRightIcon
          className="h-5 w-5 mt-1 mx-2 flex-shrink-0 text-gray-400"
          aria-hidden="true"
        />
        <p className="mt-1 max-w-2xl text-sm text-gray-500">{objectDetailsData.display_label}</p>
      </div>

      <Tabs
        tabs={tabs}
        rightItems={
          <Button onClick={() => setShowEditDrawer(true)} className="mr-4">
            Edit
            <PencilIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
          </Button>
        }
      />

      {!qspTab && (
        <div className="px-4 py-5 sm:p-0 flex-1 overflow-auto">
          <dl className="sm:divide-y sm:divide-gray-200">
            <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-3 sm:px-6">
              <dt className="text-sm font-medium text-gray-500 flex items-center">ID</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">
                {objectDetailsData.id}
              </dd>
            </div>
            {schema.attributes?.map((attribute) => {
              if (
                !objectDetailsData[attribute.name] ||
                !objectDetailsData[attribute.name].is_visible
              ) {
                return null;
              }

              return (
                <div
                  className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-3 sm:px-6"
                  key={attribute.name}>
                  <dt className="text-sm font-medium text-gray-500 flex items-center">
                    {attribute.label}
                  </dt>

                  <div className="flex items-center">
                    <dd
                      className={classNames(
                        "mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0",
                        attribute.kind === "TextArea" ? "whitespace-pre-wrap mr-2" : ""
                      )}>
                      {typeof objectDetailsData[attribute.name]?.value !== "boolean"
                        ? objectDetailsData[attribute.name].value
                          ? objectDetailsData[attribute.name].value
                          : "-"
                        : ""}
                      {typeof objectDetailsData[attribute.name]?.value === "boolean" && (
                        <>
                          {objectDetailsData[attribute.name]?.value === true && (
                            <CheckIcon className="h-4 w-4" />
                          )}
                          {objectDetailsData[attribute.name]?.value === false && (
                            <XMarkIcon className="h-4 w-4" />
                          )}
                        </>
                      )}
                    </dd>

                    {objectDetailsData[attribute.name] && (
                      <MetaDetailsTooltip
                        items={[
                          {
                            label: "Updated at",
                            value: objectDetailsData[attribute.name].updated_at,
                            type: "date",
                          },
                          {
                            label: "Update time",
                            value: `${new Date(
                              objectDetailsData[attribute.name].updated_at
                            ).toLocaleDateString()} ${new Date(
                              objectDetailsData[attribute.name].updated_at
                            ).toLocaleTimeString()}`,
                            type: "text",
                          },
                          {
                            label: "Source",
                            value: objectDetailsData[attribute.name].source,
                            type: "link",
                          },
                          {
                            label: "Owner",
                            value: objectDetailsData[attribute.name].owner,
                            type: "link",
                          },
                          {
                            label: "Is protected",
                            value: objectDetailsData[attribute.name].is_protected
                              ? "True"
                              : "False",
                            type: "text",
                          },
                          {
                            label: "Is inherited",
                            value: objectDetailsData[attribute.name].is_inherited
                              ? "True"
                              : "False",
                            type: "text",
                          },
                        ]}
                        header={
                          <div className="flex justify-between w-full py-4">
                            <div className="font-semibold">{attribute.label}</div>
                            <div
                              className="cursor-pointer"
                              onClick={() => {
                                setMetaEditFieldDetails({
                                  type: "attribute",
                                  attributeOrRelationshipName: attribute.name,
                                  label: attribute.label || attribute.name,
                                });
                                setShowMetaEditModal(true);
                              }}>
                              <PencilSquareIcon className="w-5 h-5 text-blue-500" />
                            </div>
                          </div>
                        }
                      />
                    )}

                    {objectDetailsData[attribute.name].is_protected && (
                      <LockClosedIcon className="h-5 w-5 ml-2" />
                    )}
                  </div>
                </div>
              );
            })}

            {relationships?.map((relationship: any) => {
              const relationshipSchema = schema?.relationships?.find(
                (relation) => relation?.name === relationship?.name
              );

              const relationshipData = relationship?.paginated
                ? objectDetailsData[relationship.name]?.edges
                : objectDetailsData[relationship.name];

              return (
                <RelationshipDetails
                  parentNode={objectDetailsData}
                  mode="DESCRIPTION-LIST"
                  parentSchema={schema}
                  key={relationship.name}
                  relationshipsData={relationshipData}
                  relationshipSchema={relationshipSchema}
                />
              );
            })}
          </dl>
        </div>
      )}

      {qspTab && <RelationshipsDetails parentNode={objectDetailsData} parentSchema={schema} />}

      <SlideOver
        title={
          <div className="space-y-2">
            <div className="flex items-center w-full">
              <span className="text-lg font-semibold mr-3">{objectDetailsData.display_label}</span>
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
              {schema.kind}
            </span>
            <div className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10 ml-3">
              <svg className="h-1.5 w-1.5 mr-1 fill-blue-500" viewBox="0 0 6 6" aria-hidden="true">
                <circle cx={3} cy={3} r={3} />
              </svg>
              ID: {objectDetailsData.id}
            </div>
          </div>
        }
        open={showEditDrawer}
        setOpen={setShowEditDrawer}>
        <ObjectItemEditComponent
          closeDrawer={() => {
            setShowEditDrawer(false);
          }}
          onUpdateComplete={() => {
            refetch();
          }}
          objectid={objectid!}
          objectname={objectname!}
        />
      </SlideOver>
      <SlideOver
        title={
          <div className="space-y-2">
            <div className="flex items-center w-full">
              <span className="text-lg font-semibold mr-3">{metaEditFieldDetails?.label}</span>
              <div className="flex-1"></div>
              <div className="flex items-center">
                <Square3Stack3DIcon className="w-5 h-5" />
                <div className="ml-1.5 pb-1">{branch?.name ?? DEFAULT_BRANCH_NAME}</div>
              </div>
            </div>
            <div className="text-gray-500">Metadata</div>
          </div>
        }
        open={showMetaEditModal}
        setOpen={setShowMetaEditModal}>
        <ObjectItemMetaEdit
          closeDrawer={() => setShowMetaEditModal(false)}
          onUpdateComplete={() => setShowMetaEditModal(false)}
          attributeOrRelationshipToEdit={
            objectDetailsData[metaEditFieldDetails?.attributeOrRelationshipName]
          }
          schemaList={schemaList}
          schema={schema}
          attributeOrRelationshipName={metaEditFieldDetails?.attributeOrRelationshipName}
          type={metaEditFieldDetails?.type!}
          row={objectDetailsData}
        />
      </SlideOver>
    </div>
  );
}