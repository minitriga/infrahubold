import {
  EyeSlashIcon,
  LockClosedIcon,
  PencilSquareIcon,
  PlusIcon,
  Square3Stack3DIcon,
} from "@heroicons/react/24/outline";
import { useAtom } from "jotai";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Link } from "../../components/link";
import MetaDetailsTooltip from "../../components/meta-details-tooltips";
import ModalDelete from "../../components/modal-delete";
import { RoundedButton } from "../../components/rounded-button";
import { SelectOption } from "../../components/select";
import SlideOver from "../../components/slide-over";
import { showMetaEditState } from "../../state/atoms/metaEditFieldDetails.atom";
import {
  genericsState,
  iNodeSchema,
  schemaState,
} from "../../state/atoms/schema.atom";
import { schemaKindNameState } from "../../state/atoms/schemaKindName.atom";
import { metaEditFieldDetailsState } from "../../state/atoms/showMetaEdit.atom copy";
import { classNames } from "../../utils/common";
import { constructPath } from "../../utils/fetch";
import { getObjectItemDisplayValue } from "../../utils/getObjectItemDisplayValue";
import { getAttributeColumnsFromNodeOrGenericSchema } from "../../utils/getSchemaObjectColumns";
import { getObjectDetailsUrl } from "../../utils/objects";
import updateObjectWithId from "../../utils/updateObjectWithId";
import { DynamicFieldData } from "../edit-form-hook/dynamic-control-types";
import EditFormHookComponent from "../edit-form-hook/edit-form-hook-component";
import NoDataFound from "../no-data-found/no-data-found";
import ObjectItemEditComponent from "../object-item-edit/object-item-edit.component";
import ObjectItemMetaEdit from "../object-item-meta-edit/object-item-meta-edit";
import { toast } from "react-toastify";
import { ALERT_TYPES, Alert } from "../../components/alert";
import { branchState } from "../../state/atoms/branch.atom";
import { DEFAULT_BRANCH_NAME } from "../../config/constants";

type iRelationDetailsProps = {
  parentNode: any;
  parentSchema: iNodeSchema;
  refreshObject: Function;
  relationshipsData: any;
  relationshipSchema: any;
  mode: "TABLE" | "DESCRIPTION-LIST";
};

const regex = /^Related/; // starts with Related

export default function RelationshipDetails(props: iRelationDetailsProps) {
  const { objectname, objectid } = useParams();
  const [branch] = useAtom(branchState);
  const { relationshipsData, relationshipSchema, refreshObject } = props;
  const [schemaList] = useAtom(schemaState);
  const [generics] = useAtom(genericsState);
  const [showAddDrawer, setShowAddDrawer] = useState(false);
  const schema = schemaList.filter((s) => s.name === objectname)[0];
  const [showRelationMetaEditModal, setShowRelationMetaEditModal] =
    useState(false);
  const [rowForMetaEdit, setRowForMetaEdit] = useState<any>();
  const [relatedRowToDelete, setRelatedRowToDelete] = useState<any>();
  const [relatedObjectToEdit, setRelatedObjectToEdit] = useState<any>();

  let options: SelectOption[] = [];

  const generic = generics.find((g) => g.kind === relationshipSchema.peer);

  if (generic) {
    (generic.used_by || []).forEach((name) => {
      const relatedSchema = schemaList.find((s) => s.kind === name);

      if (relatedSchema) {
        options.push({
          id: relatedSchema.name,
          name: name,
        });
      }
    });
  } else {
    const relatedSchema = schemaList.find(
      (s) => s.kind === relationshipSchema.peer
    );

    if (relatedSchema) {
      options.push({
        id: relatedSchema.name,
        name: relatedSchema.label ?? relatedSchema.name,
      });
    }
  }

  const formFields: DynamicFieldData[] = [
    {
      kind: "Text",
      label: relationshipSchema.label,
      name: "id",
      options: {
        values: options,
      },
      type: "select2step",
      value: {},
      config: {},
    },
  ];

  const [schemaKindName] = useAtom(schemaKindNameState);
  const navigate = useNavigate();

  const [, setShowMetaEditModal] = useAtom(showMetaEditState);
  const [, setMetaEditFieldDetails] = useAtom(metaEditFieldDetailsState);

  const columns = getAttributeColumnsFromNodeOrGenericSchema(
    schemaList,
    generics,
    relationshipSchema.peer
  );

  if (relationshipsData && relationshipsData._relation__is_visible === false) {
    return null;
  }

  if (
    relationshipSchema?.cardinality === "many" &&
    !Array.isArray(relationshipsData)
  ) {
    return null;
  }

  const handleDeleteRelationship = async (id: string) => {
    const newList = relationshipsData
      .map((item: any) => ({ id: item.id }))
      .filter((item: any) => item.id !== id);

    await updateObjectWithId(objectid!, schema, {
      [relationshipSchema.name]: newList,
    });

    refreshObject();

    setShowAddDrawer(false);
    toast(
      <Alert
        type={ALERT_TYPES.SUCCESS}
        message={`Association with ${relationshipSchema.peer} removed`}
      />
    );
  };

  return (
    <>
      <div key={relationshipSchema?.name}>
        {!relationshipsData && (
          <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-4 sm:px-6">
            <dt className="text-sm font-medium text-gray-500 flex items-center">
              {relationshipSchema?.label}
            </dt>
            <dd className="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0 flex items-center">
              -
            </dd>
          </div>
        )}
        {relationshipsData && (
          <>
            {relationshipSchema?.cardinality === "one" && (
              <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-3 sm:px-6">
                <dt className="text-sm font-medium text-gray-500 flex items-center">
                  {relationshipSchema?.label}
                </dt>
                <dd className="mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0 underline flex items-center">
                  <Link
                    onClick={() =>
                      navigate(
                        constructPath(
                          getObjectDetailsUrl(
                            relationshipsData,
                            schemaKindName,
                            relationshipsData.id
                          )
                        )
                      )
                    }
                  >
                    {relationshipsData.display_label}
                  </Link>

                  {relationshipsData && (
                    <MetaDetailsTooltip
                      items={[
                        {
                          label: "Updated at",
                          value: relationshipsData._updated_at,
                          type: "date",
                        },
                        {
                          label: "Update time",
                          value: `${new Date(
                            relationshipsData._updated_at
                          ).toLocaleDateString()} ${new Date(
                            relationshipsData._updated_at
                          ).toLocaleTimeString()}`,
                          type: "text",
                        },
                        {
                          label: "Source",
                          value: relationshipsData._relation__source,
                          type: "link",
                        },
                        {
                          label: "Owner",
                          value: relationshipsData._relation__owner,
                          type: "link",
                        },
                        {
                          label: "Is protected",
                          value: relationshipsData._relation__is_protected
                            ? "True"
                            : "False",
                          type: "text",
                        },
                      ]}
                      header={
                        <div className="flex justify-between w-full py-4">
                          <div className="font-semibold">
                            {relationshipSchema.label}
                          </div>
                          <div
                            className="cursor-pointer"
                            onClick={() => {
                              setMetaEditFieldDetails({
                                type: "relationship",
                                attributeOrRelationshipName:
                                  relationshipSchema.name,
                                label:
                                  relationshipSchema.label ||
                                  relationshipSchema.name,
                              });
                              setShowMetaEditModal(true);
                            }}
                          >
                            <PencilSquareIcon className="w-5 h-5 text-blue-500" />
                          </div>
                        </div>
                      }
                    />
                  )}

                  {relationshipsData._relation__is_protected && (
                    <LockClosedIcon className="h-5 w-5 ml-2" />
                  )}

                  {relationshipsData._relation__is_visible === false && (
                    <EyeSlashIcon className="h-5 w-5 ml-2" />
                  )}
                </dd>
              </div>
            )}

            {relationshipSchema?.cardinality === "many" &&
              props.mode === "TABLE" && (
                <div className="mt-0 flex flex-col px-4 sm:px-6 lg:px-8 w-full flex-1">
                  <div className="-my-2 -mx-4 sm:-mx-6 lg:-mx-8">
                    <div className="inline-block min-w-full pt-2 align-middle">
                      <div className="shadow-sm ring-1 ring-black ring-opacity-5">
                        <table
                          className="min-w-full border-separate"
                          style={{ borderSpacing: 0 }}
                        >
                          <thead className="bg-gray-50">
                            <tr>
                              {columns?.map((column) => (
                                <th
                                  key={column.name}
                                  scope="col"
                                  className="sticky top-0 border-b border-gray-300 bg-gray-50 bg-opacity-75 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 backdrop-blur backdrop-filter sm:pl-6 lg:pl-8"
                                >
                                  {column.label}
                                </th>
                              ))}
                              <th
                                scope="col"
                                className="sticky top-0 border-b border-gray-300 bg-gray-50 bg-opacity-75 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 backdrop-blur backdrop-filter sm:pl-6 lg:pl-8"
                              >
                                <span className="sr-only">Meta</span>
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white">
                            {relationshipsData?.map(
                              (row: any, index: number) => (
                                <tr
                                  onClick={() =>
                                    navigate(
                                      getObjectDetailsUrl(
                                        row,
                                        schemaKindName,
                                        row.id
                                      )
                                    )
                                  }
                                  key={index}
                                  className="hover:bg-gray-50 cursor-pointer"
                                >
                                  {columns?.map((column) => (
                                    <td
                                      key={row.id + "-" + column.name}
                                      className={classNames(
                                        index !== relationshipsData.length - 1
                                          ? "border-b border-gray-200"
                                          : "",
                                        "whitespace-nowrap py-3 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6 lg:pl-8"
                                      )}
                                    >
                                      {getObjectItemDisplayValue(row, column)}
                                    </td>
                                  ))}
                                  <td
                                    className={classNames(
                                      index !== relationshipsData.length - 1
                                        ? "border-b border-gray-200"
                                        : "",
                                      "whitespace-nowrap py-3 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6 lg:pl-8 flex items-center space-x-3"
                                    )}
                                  >
                                    <div
                                      className="cursor-pointer w-7 h-7 flex items-center justify-center"
                                      onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        setRowForMetaEdit(row);
                                        setShowRelationMetaEditModal(true);
                                      }}
                                    >
                                      <MetaDetailsTooltip
                                        position="LEFT"
                                        items={[
                                          {
                                            label: "Updated at",
                                            value: row._updated_at,
                                            type: "date",
                                          },
                                          {
                                            label: "Update time",
                                            value: `${new Date(
                                              row._updated_at
                                            ).toLocaleDateString()} ${new Date(
                                              row._updated_at
                                            ).toLocaleTimeString()}`,
                                            type: "text",
                                          },
                                          {
                                            label: "Source",
                                            value: row._relation__source,
                                            type: "link",
                                          },
                                          {
                                            label: "Owner",
                                            value: row._relation__owner,
                                            type: "link",
                                          },
                                          {
                                            label: "Is protected",
                                            value: row._relation__is_protected
                                              ? "True"
                                              : "False",
                                            type: "text",
                                          },
                                        ]}
                                      />
                                    </div>
                                    <div
                                      className="cursor-pointer w-7 h-7 flex items-center justify-center"
                                      onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        setRelatedObjectToEdit(row);
                                      }}
                                    >
                                      <PencilSquareIcon className="w-6 h-6 text-gray-600 hover:w-7 hover:h-7" />
                                    </div>
                                    <div
                                      className="cursor-pointer w-7 h-7 flex items-center justify-center"
                                      onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        setRelatedRowToDelete(row);
                                      }}
                                    >
                                      <img
                                        alt="unlink"
                                        src={
                                          process.env.PUBLIC_URL +
                                          "/images/icons/unlink.png"
                                        }
                                        className="w-5 h-5 hover:w-6 hover:h-6"
                                      />
                                    </div>
                                  </td>
                                </tr>
                              )
                            )}
                          </tbody>
                        </table>

                        {relationshipsData && !relationshipsData.length && (
                          <NoDataFound />
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

            {relationshipSchema?.cardinality === "many" &&
              props.mode === "DESCRIPTION-LIST" && (
                <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-3 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500 flex items-center">
                    {relationshipSchema?.label}
                  </dt>
                  <dl className="sm:divide-y sm:divide-gray-200">
                    <div className="sm:col-span-2 space-y-4">
                      {relationshipsData.length === 0 && "-"}
                      {relationshipsData?.map((item: any) => (
                        <dd
                          className="mt-1 text-sm text-gray-900 sm:mt-0 underline flex items-center"
                          key={item.id}
                        >
                          <Link
                            onClick={() =>
                              navigate(
                                constructPath(
                                  getObjectDetailsUrl(
                                    item,
                                    schemaKindName,
                                    item.id
                                  )
                                )
                              )
                            }
                          >
                            {item.display_label}
                          </Link>

                          {item && (
                            <MetaDetailsTooltip
                              items={[
                                {
                                  label: "Updated at",
                                  value: item._updated_at,
                                  type: "date",
                                },
                                {
                                  label: "Update time",
                                  value: `${new Date(
                                    item._updated_at
                                  ).toLocaleDateString()} ${new Date(
                                    item._updated_at
                                  ).toLocaleTimeString()}`,
                                  type: "text",
                                },
                                {
                                  label: "Source",
                                  value: item._relation__source,
                                  type: "link",
                                },
                                {
                                  label: "Owner",
                                  value: item._relation__owner,
                                  type: "link",
                                },
                                {
                                  label: "Is protected",
                                  value: item._relation__is_protected
                                    ? "True"
                                    : "False",
                                  type: "text",
                                },
                              ]}
                            />
                          )}

                          {item._relation__is_protected && (
                            <LockClosedIcon className="h-5 w-5 ml-2" />
                          )}

                          {item._relation__is_visible === false && (
                            <EyeSlashIcon className="h-5 w-5 ml-2" />
                          )}
                          {/* {<TrashIcon className="h-5 w-5 ml-2" onClick={async () => {
                            const newList  = relationshipsData.map((row: any) => ({ id: row.id })).filter((row: any) =>  row.id !== item.id);
                            await updateObjectWithId(objectid!, schema, {
                              [relationshipSchema.name]: newList
                            });
                            props.refreshObject();
                            setShowAddDrawer(false);
                          }}/>} */}
                        </dd>
                      ))}
                    </div>
                  </dl>
                </div>
              )}
          </>
        )}
        {props.mode === "TABLE" && (
          <div className="absolute bottom-4 right-4">
            <RoundedButton
              onClick={() => setShowAddDrawer(true)}
              className="p-3 ml-2 bg-blue-500 text-sm hover:bg-blue-600 focus:ring-blue-500 focus:ring-offset-gray-50 focus:ring-offset-2"
            >
              <PlusIcon className="h-7 w-7 text-white" aria-hidden="true" />
            </RoundedButton>
          </div>
        )}
        <SlideOver
          title={
            <div className="space-y-2">
              <div className="flex items-center w-full">
                <span className="text-lg font-semibold mr-3">
                  Add associated {relationshipSchema.label}
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
                {relationshipSchema.peer}
              </span>
            </div>
          }
          open={showAddDrawer}
          setOpen={setShowAddDrawer}
        >
          <EditFormHookComponent
            onCancel={() => {
              setShowAddDrawer(false);
            }}
            onSubmit={async (data) => {
              if (data?.id) {
                const newList = [
                  ...relationshipsData.map((row: any) => ({ id: row.id })),
                  { id: data.id },
                ];
                await updateObjectWithId(objectid!, schema, {
                  [relationshipSchema.name]: newList,
                });
                props.refreshObject();
                toast(
                  <Alert
                    type={ALERT_TYPES.SUCCESS}
                    message={`Association with ${relationshipSchema.peer} added`}
                  />
                );
                setShowAddDrawer(false);
              }
            }}
            fields={formFields}
          />
        </SlideOver>
        <SlideOver
          title={
            <>
              {rowForMetaEdit && (
                <div className="space-y-2">
                  <div className="flex items-center w-full">
                    <span className="text-lg font-semibold mr-3">
                      {props.parentNode?.display_label} -{" "}
                      {rowForMetaEdit.display_label}
                    </span>
                    <div className="flex-1"></div>
                    <div className="flex items-center">
                      <Square3Stack3DIcon className="w-5 h-5" />
                      <div className="ml-1.5 pb-1">
                        {branch?.name ?? DEFAULT_BRANCH_NAME}
                      </div>
                    </div>
                  </div>
                  <div className="text-gray-500">Association metadata</div>
                </div>
              )}
            </>
          }
          open={showRelationMetaEditModal}
          setOpen={setShowRelationMetaEditModal}
        >
          <ObjectItemMetaEdit
            closeDrawer={() => {
              setShowRelationMetaEditModal(false);
            }}
            onUpdateComplete={() => {
              setShowRelationMetaEditModal(false);
              props.refreshObject();
            }}
            attributeOrRelationshipToEdit={rowForMetaEdit}
            schemaList={schemaList}
            schema={schema}
            attributeOrRelationshipName={relationshipSchema.name}
            type="relationship"
            row={{
              ...props.parentNode,
              [relationshipSchema.name]: relationshipsData,
            }}
          />
        </SlideOver>
        {relatedRowToDelete && (
          <ModalDelete
            title="Delete"
            description={
              <>
                Are you sure you want to remove the association between{" "}
                <b>`{props.parentNode.display_label}`</b> and{" "}
                <b>`{relatedRowToDelete.display_label}`</b>? The{" "}
                <b>`{relatedRowToDelete.__typename.replace(regex, "")}`</b>{" "}
                <b>`{relatedRowToDelete.display_label}`</b> won&apos;t be
                deleted in the process.
              </>
            }
            onCancel={() => setRelatedRowToDelete(undefined)}
            onDelete={() => {
              if (relatedRowToDelete?.id) {
                handleDeleteRelationship(relatedRowToDelete.id);
              }
            }}
            open={!!relatedRowToDelete}
            setOpen={() => setRelatedRowToDelete(undefined)}
          />
        )}
        {relatedObjectToEdit && (
          <SlideOver
            title={
              <>
                {
                  <div className="space-y-2">
                    <div className="flex items-center w-full">
                      <span className="text-lg font-semibold mr-3">
                        {relatedObjectToEdit?.display_label}
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
                      {relatedObjectToEdit?.__typename.replace(regex, "")}
                    </span>
                  </div>
                }
              </>
            }
            open={!!relatedObjectToEdit}
            setOpen={() => setRelatedObjectToEdit(undefined)}
          >
            <ObjectItemEditComponent
              closeDrawer={() => {
                setRelatedObjectToEdit(undefined);
              }}
              onUpdateComplete={async () => {
                setRelatedObjectToEdit(undefined);
                await refreshObject();
              }}
              objectid={relatedObjectToEdit.id}
              objectname={(() => {
                const relatedKind = relatedObjectToEdit.__typename.replace(
                  regex,
                  ""
                );
                console.log(relatedKind);
                const relatedSchema = schemaList.find(
                  (s) => s.kind === relatedKind
                );
                const kind = schemaKindName[relatedSchema!.kind];
                console.log("Kind: ", kind);
                return kind;
              })()}
            />
          </SlideOver>
        )}
      </div>
    </>
  );
}
