import * as R from "ramda";
import {
  attributesKindForDetailsViewExclude,
  attributesKindForListView,
  peersKindForForm,
  relationshipsForDetailsView,
  relationshipsForListView,
  relationshipsForTabs,
} from "../config/constants";
import { iGenericSchema, iNodeSchema } from "../state/atoms/schema.atom";

export const getObjectAttributes = (
  schema: iNodeSchema | iGenericSchema,
  forListView?: boolean
) => {
  if (!schema) {
    return [];
  }

  const attributes = (schema.attributes || [])
    .filter((attribute) =>
      forListView
        ? attributesKindForListView.includes(attribute.kind)
        : !attributesKindForDetailsViewExclude.includes(attribute.kind)
    )
    .map((row) => ({
      label: row.label ?? "",
      name: row.name,
      kind: row.kind,
    }));

  return attributes;
};

export const getObjectRelationships = (
  schema?: iNodeSchema | iGenericSchema,
  forListView?: boolean
) => {
  if (!schema) {
    return [];
  }

  const kinds = forListView ? relationshipsForListView : relationshipsForDetailsView;

  const relationships = (schema.relationships || [])
    .filter((relationship) => kinds[relationship.cardinality].includes(relationship.kind ?? ""))
    .map((relationship) => ({
      label: relationship.label ?? "",
      name: relationship.name,
      paginated: relationship.cardinality === "many",
    }));

  return relationships;
};

export const getTabs = (schema: iNodeSchema | iGenericSchema) => {
  if (!schema) {
    return [];
  }

  // Relationship kind to show in LIST VIEW - Attribute, Parent
  const relationships = (schema.relationships || [])
    .filter((relationship) =>
      relationshipsForTabs[relationship.cardinality].includes(relationship.kind)
    )
    .map((relationship) => ({
      label: relationship.label,
      name: relationship.name,
    }));

  return relationships;
};

export const getSchemaObjectColumns = (schema?: iNodeSchema | iGenericSchema) => {
  if (!schema) {
    return [];
  }

  const attributes = getObjectAttributes(schema, true);
  const relationships = getObjectRelationships(schema, true);

  const columns = R.concat(attributes, relationships);
  return columns;
};

export const getGroupColumns = (schema?: iNodeSchema | iGenericSchema) => {
  if (!schema) {
    return [];
  }

  const defaultColumns = [{ label: "Type", name: "__typename" }];
  const attributes = getObjectAttributes(schema);
  const relationships = getObjectRelationships(schema);

  const columns = R.concat(attributes, relationships);

  return [...defaultColumns, ...columns];
};

export const getAttributeColumnsFromNodeOrGenericSchema = (
  schema: iNodeSchema | undefined,
  generic: iGenericSchema | undefined
) => {
  if (generic) {
    return getSchemaObjectColumns(generic);
  }

  if (schema) {
    return getSchemaObjectColumns(schema);
  }

  return [];
};

export const getObjectTabs = (tabs: any[], data: any) => {
  return tabs.map((tab: any) => ({
    ...tab,
    count: data[tab.name].count,
  }));
};

// Used by the form to display the fields
export const getObjectRelationshipsForForm = (schema?: iNodeSchema | iGenericSchema) => {
  const relationships = (schema?.relationships || [])
    .filter(
      (relationship) =>
        peersKindForForm.includes(relationship?.kind ?? "") || relationship.cardinality === "one"
    )
    .filter(Boolean);

  return relationships;
};

// Used by the query to retrieve the data for the form
export const getObjectPeers = (schema?: iNodeSchema | iGenericSchema) => {
  const peers = getObjectRelationshipsForForm(schema)
    .map((relationship) => relationship.peer)
    .filter(Boolean);

  return peers;
};
