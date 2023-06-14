from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union

import graphene

import infrahub.config as config
from infrahub.core import get_branch, registry
from infrahub.core.manager import NodeManager
from infrahub.core.schema import GenericSchema, GroupSchema, NodeSchema
from infrahub.types import ATTRIBUTE_TYPES

from .mutations import InfrahubMutation, InfrahubRepositoryMutation
from .schema import default_paginated_list_resolver
from .types import (
    RELATIONS_PROPERTY_MAP,
    RELATIONS_PROPERTY_MAP_REVERSED,
    InfrahubInterface,
    InfrahubObject,
    InfrahubUnion,
    RelatedNodeInput,
    RelatedNodeInterface,
)
from .utils import extract_fields

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo
    from neo4j import AsyncSession

    from infrahub.core.branch import Branch

# pylint: disable=protected-access,too-many-locals,too-many-lines

EXCLUDED_ATTRIBUTE_KINDS = ["HashedPassword"]


class DeleteInput(graphene.InputObjectType):
    id = graphene.String(required=True)


async def default_resolver(*args, **kwargs):
    """Not sure why but the default resolver returns sometime 4 positional args and sometime 2.

    When it returns 4, they are organized as follow
        - field name
        - ???
        - parent
        - info
    When it returns 2, they are organized as follow
        - parent
        - info
    """

    parent = None
    info = None
    field_name = None

    if len(args) == 4:
        parent = args[2]
        info = args[3]
        field_name = args[0]
    elif len(args) == 2:
        parent = args[0]
        info = args[1]
        field_name = info.field_name
    else:
        raise ValueError(f"expected either 2 or 4 args for default_resolver, got {len(args)}")

    # Extract the InfraHub schema by inspecting the GQL Schema
    node_schema: NodeSchema = info.parent_type.graphene_type._meta.schema

    # If the field is an attribute, return its value directly
    if field_name not in node_schema.relationship_names:
        return parent.get(field_name, None)

    # Extract the contextual information from the request context
    at = info.context.get("infrahub_at")
    branch = info.context.get("infrahub_branch")
    # account = info.context.get("infrahub_account", None)
    db = info.context.get("infrahub_database")

    # Extract the name of the fields in the GQL query
    fields = await extract_fields(info.field_nodes[0].selection_set)

    # Extract the schema of the node on the other end of the relationship from the GQL Schema
    node_rel = node_schema.get_relationship(info.field_name)

    # Extract only the filters from the kwargs and prepend the name of the field to the filters
    filters = {
        f"{info.field_name}__{key}": value for key, value in kwargs.items() if "__" in key and value or key == "id"
    }

    async with db.session(database=config.SETTINGS.database.database) as new_session:
        objs = await NodeManager.query_peers(
            session=new_session,
            id=parent["id"],
            schema=node_rel,
            filters=filters,
            fields=fields,
            at=at,
            branch=branch,
        )

        if node_rel.cardinality == "many":
            return [await obj.to_graphql(session=new_session, fields=fields) for obj in objs]

        # If cardinality is one
        if not objs:
            return None

        return await objs[0].to_graphql(session=new_session, fields=fields)


async def relationship_resolver(parent: dict, info: GraphQLResolveInfo, **kwargs) -> Optional[Union[Dict, List]]:
    # Extract the InfraHub schema by inspecting the GQL Schema
    node_schema: NodeSchema = info.parent_type.graphene_type._meta.schema

    # Extract the contextual information from the request context
    at = info.context.get("infrahub_at")
    branch = info.context.get("infrahub_branch")
    db = info.context.get("infrahub_database")

    # Extract the name of the fields in the GQL query
    fields = await extract_fields(info.field_nodes[0].selection_set)

    # Extract the schema of the node on the other end of the relationship from the GQL Schema
    node_rel = node_schema.get_relationship(info.field_name)

    # Extract only the filters from the kwargs and prepend the name of the field to the filters
    filters = {
        f"{info.field_name}__{key}": value for key, value in kwargs.items() if "__" in key and value or key == "id"
    }

    async with db.session(database=config.SETTINGS.database.database) as new_session:
        objs = await NodeManager.query_peers(
            session=new_session,
            id=parent["id"],
            schema=node_rel,
            filters=filters,
            fields=fields,
            at=at,
            branch=branch,
        )

        if node_rel.cardinality == "many":
            return [await obj.to_graphql(session=new_session, fields=fields) for obj in objs]

        # If cardinality is one
        if not objs:
            return None

        return await objs[0].to_graphql(session=new_session, fields=fields)


async def single_relationship_resolver(parent: dict, info: GraphQLResolveInfo, **kwargs) -> Dict[str, Any]:
    """Resolver for relationships of cardinality=one for Edged responses

    This resolver is used for paginated responses and as such we redefined the requested
    fields by only reusing information below the 'node' key.
    """
    # Extract the InfraHub schema by inspecting the GQL Schema

    node_schema: NodeSchema = info.parent_type.graphene_type._meta.schema

    # Extract the contextual information from the request context
    at = info.context.get("infrahub_at")
    branch = info.context.get("infrahub_branch")
    db = info.context.get("infrahub_database")

    # Extract the name of the fields in the GQL query
    fields = await extract_fields(info.field_nodes[0].selection_set)
    node_fields = fields.get("node", {})
    property_fields = fields.get("properties", {})
    for key, value in property_fields.items():
        mapped_name = RELATIONS_PROPERTY_MAP[key]
        node_fields[mapped_name] = value

    # Extract the schema of the node on the other end of the relationship from the GQL Schema
    node_rel = node_schema.get_relationship(info.field_name)
    # Extract only the filters from the kwargs and prepend the name of the field to the filters
    filters = {
        f"{info.field_name}__{key}": value for key, value in kwargs.items() if "__" in key and value or key == "id"
    }
    response: Dict[str, Any] = {"node": None, "properties": {}}
    async with db.session(database=config.SETTINGS.database.database) as new_session:
        objs = await NodeManager.query_peers(
            session=new_session,
            id=parent["id"],
            schema=node_rel,
            filters=filters,
            fields=node_fields,
            at=at,
            branch=branch,
        )

        if not objs:
            return response

        node_graph = await objs[0].to_graphql(session=new_session, fields=node_fields)
        for key, mapped in RELATIONS_PROPERTY_MAP_REVERSED.items():
            value = node_graph.pop(key, None)
            if value:
                response["properties"][mapped] = value
        response["node"] = node_graph
        return response


async def many_relationship_resolver(parent: dict, info: GraphQLResolveInfo, **kwargs) -> Dict[str, Any]:
    """Resolver for relationships of cardinality=many for Edged responses

    This resolver is used for paginated responses and as such we redefined the requested
    fields by only reusing information below the 'node' key.
    """
    # Extract the InfraHub schema by inspecting the GQL Schema
    node_schema: NodeSchema = info.parent_type.graphene_type._meta.schema

    # Extract the contextual information from the request context
    at = info.context.get("infrahub_at")
    branch = info.context.get("infrahub_branch")
    db = info.context.get("infrahub_database")

    # Extract the name of the fields in the GQL query
    fields = await extract_fields(info.field_nodes[0].selection_set)
    edges = fields.get("edges", {})
    node_fields = edges.get("node", {})
    property_fields = edges.get("properties", {})
    for key, value in property_fields.items():
        mapped_name = RELATIONS_PROPERTY_MAP[key]
        node_fields[mapped_name] = value

    # Extract the schema of the node on the other end of the relationship from the GQL Schema
    node_rel = node_schema.get_relationship(info.field_name)

    # Extract only the filters from the kwargs and prepend the name of the field to the filters
    offset = kwargs.pop("offset", None)
    limit = kwargs.pop("limit", None)
    filters = {
        f"{info.field_name}__{key}": value for key, value in kwargs.items() if "__" in key and value or key == "id"
    }

    response: Dict[str, Any] = {"edges": [], "count": None}
    async with db.session(database=config.SETTINGS.database.database) as new_session:
        if "count" in fields:
            response["count"] = await NodeManager.count_peers(
                session=new_session,
                id=parent["id"],
                schema=node_rel,
                filters=filters,
                at=at,
                branch=branch,
            )
        objs = await NodeManager.query_peers(
            session=new_session,
            id=parent["id"],
            schema=node_rel,
            filters=filters,
            fields=node_fields,
            offset=offset,
            limit=limit,
            at=at,
            branch=branch,
        )

        if not objs:
            return response
        node_graph = [await obj.to_graphql(session=new_session, fields=node_fields) for obj in objs]

        entries = []
        for node in node_graph:
            entry = {"node": {}, "properties": {}}
            for key, mapped in RELATIONS_PROPERTY_MAP_REVERSED.items():
                value = node.pop(key, None)
                if value:
                    entry["properties"][mapped] = value
            entry["node"] = node
            entries.append(entry)
        response["edges"] = entries

        return response


def load_attribute_types_in_registry(branch: Branch):
    for data_type in ATTRIBUTE_TYPES.values():
        registry.set_graphql_type(
            name=data_type.get_graphql_type_name(), graphql_type=data_type.get_graphql_type(), branch=branch.name
        )


async def generate_object_types(
    session: AsyncSession, branch: Union[Branch, str]
):  # pylint: disable=too-many-branches,too-many-statements
    """Generate all GraphQL objects for the schema and store them in the internal registry."""

    branch = await get_branch(session=session, branch=branch)

    full_schema = await registry.schema.get_full_safe(branch=branch)

    group_memberships = defaultdict(list)

    load_attribute_types_in_registry(branch=branch)

    # Generate all GraphQL Interface & RelatedInterface Object first and store them in the registry
    for node_name, node_schema in full_schema.items():
        if not isinstance(node_schema, GenericSchema):
            continue
        interface = generate_interface_object(schema=node_schema, branch=branch)
        registry.set_graphql_type(name=interface._meta.name, graphql_type=interface, branch=branch.name)

    # Define DataOwner and DataOwner
    data_source = registry.get_graphql_type(name="DataSource", branch=branch)
    data_owner = registry.get_graphql_type(name="DataOwner", branch=branch)
    define_relationship_property(branch=branch, data_source=data_source, data_owner=data_owner)
    relationship_property = registry.get_graphql_type(name="RelationshipProperty", branch=branch)
    for data_type in ATTRIBUTE_TYPES.values():
        gql_type = registry.get_graphql_type(name=data_type.get_graphql_type_name(), branch=branch)
        gql_type._meta.fields["source"] = graphene.Field(data_source)
        gql_type._meta.fields["owner"] = graphene.Field(data_owner)

    # Generate all RelatedInterfaceType and store them in the registry
    for node_name, node_schema in full_schema.items():
        if not isinstance(node_schema, GenericSchema):
            continue

        related_interface = generate_related_interface_object(
            schema=node_schema, branch=branch, data_source=data_source, data_owner=data_owner, name_prefix="Related"
        )
        node_interface = registry.get_graphql_type(name=node_name, branch=branch)

        nested_edged_interface = generate_nested_interface_object(
            schema=node_schema,
            base_interface=node_interface,
            relation_property=relationship_property,
        )

        nested_interface = generate_paginated_interface_object(
            schema=node_schema,
            base_interface=nested_edged_interface,
        )

        registry.set_graphql_type(name=related_interface._meta.name, graphql_type=related_interface, branch=branch.name)
        registry.set_graphql_type(name=nested_interface._meta.name, graphql_type=nested_interface, branch=branch.name)
        registry.set_graphql_type(
            name=nested_edged_interface._meta.name, graphql_type=nested_edged_interface, branch=branch.name
        )

    # Generate all GraphQL ObjectType & RelatedObjectType and store them in the registry
    for node_name, node_schema in full_schema.items():
        if isinstance(node_schema, NodeSchema):
            node_type = generate_graphql_object(schema=node_schema, branch=branch)
            related_node_type = generate_related_graphql_object(
                schema=node_schema, branch=branch, data_source=data_source, data_owner=data_owner
            )

            node_type_edged = generate_graphql_edged_object(schema=node_schema, node=node_type)
            nested_node_type_edged = generate_graphql_edged_object(
                schema=node_schema, node=node_type, relation_property=relationship_property
            )

            node_type_paginated = generate_graphql_paginated_object(schema=node_schema, edge=node_type_edged)
            node_type_nested_paginated = generate_graphql_paginated_object(
                schema=node_schema, edge=nested_node_type_edged, nested=True
            )

            registry.set_graphql_type(name=node_type._meta.name, graphql_type=node_type, branch=branch.name)
            registry.set_graphql_type(
                name=related_node_type._meta.name, graphql_type=related_node_type, branch=branch.name
            )
            registry.set_graphql_type(name=node_type_edged._meta.name, graphql_type=node_type_edged, branch=branch.name)
            registry.set_graphql_type(
                name=nested_node_type_edged._meta.name, graphql_type=nested_node_type_edged, branch=branch.name
            )

            registry.set_graphql_type(
                name=node_type_paginated._meta.name, graphql_type=node_type_paginated, branch=branch.name
            )
            registry.set_graphql_type(
                name=node_type_nested_paginated._meta.name, graphql_type=node_type_nested_paginated, branch=branch.name
            )

            # Register this model to all the groups it belongs to.
            if node_schema.groups:
                for group_name in node_schema.groups:
                    group_memberships[group_name].append(f"Related{node_schema.kind}")

    # Generate all the Groups with associated ObjectType / RelatedObjectType
    for node_name, node_schema in full_schema.items():
        if (
            not isinstance(node_schema, GroupSchema)
            or node_name not in group_memberships
            or not group_memberships[node_name]
        ):
            continue
        group = generate_union_object(schema=node_schema, members=group_memberships.get(node_name, []), branch=branch)
        registry.set_graphql_type(name=group._meta.name, graphql_type=group, branch=branch.name)

    # Extend all types and related types with Relationships
    for node_name, node_schema in full_schema.items():
        if not isinstance(node_schema, (NodeSchema, GenericSchema)):
            continue
        node_type = registry.get_graphql_type(name=node_name, branch=branch.name)

        for rel in node_schema.relationships:
            peer_schema = await rel.get_peer_schema(branch=branch)

            peer_filters = await generate_filters(session=session, schema=peer_schema, top_level=False)

            if rel.cardinality == "one":
                if isinstance(peer_schema, GroupSchema):
                    peer_type = registry.get_graphql_type(name=peer_schema.kind, branch=branch.name)
                else:
                    peer_type = registry.get_graphql_type(name=f"NestedEdged{peer_schema.kind}", branch=branch.name)
                node_type._meta.fields[rel.name] = graphene.Field(peer_type, resolver=single_relationship_resolver)

            elif rel.cardinality == "many":
                if isinstance(peer_schema, GroupSchema):
                    peer_type = registry.get_graphql_type(name=peer_schema.kind, branch=branch.name)
                else:
                    peer_type = registry.get_graphql_type(name=f"NestedPaginated{peer_schema.kind}", branch=branch.name)
                node_type._meta.fields[rel.name] = graphene.Field(
                    peer_type, required=False, resolver=many_relationship_resolver, **peer_filters
                )


async def generate_query_mixin(session: AsyncSession, branch: Union[Branch, str] = None) -> Type[object]:
    class_attrs = {}

    full_schema = await registry.schema.get_full_safe(branch=branch)

    # Generate all Graphql objectType and store them in the registry
    await generate_object_types(session=session, branch=branch)

    for node_name, node_schema in full_schema.items():
        if not isinstance(node_schema, NodeSchema):
            continue

        node_type = registry.get_graphql_type(name=f"Paginated{node_name}", branch=branch)
        node_filters = await generate_filters(session=session, schema=node_schema, top_level=True)

        class_attrs[node_schema.name] = graphene.Field(
            node_type,
            resolver=default_paginated_list_resolver,
            **node_filters,
        )

    return type("QueryMixin", (object,), class_attrs)


async def generate_mutation_mixin(session: AsyncSession, branch: Union[Branch, str] = None) -> Type[object]:
    class_attrs = {}

    branch = await get_branch(branch=branch, session=session)

    full_schema = registry.schema.get_full(branch=branch)

    for node_schema in full_schema.values():
        if not isinstance(node_schema, NodeSchema):
            continue

        base_class = InfrahubMutation
        if node_schema.name == "repository":
            base_class = InfrahubRepositoryMutation

        create, update, delete = generate_graphql_mutations(branch=branch, schema=node_schema, base_class=base_class)

        class_attrs[f"{node_schema.name}_create"] = create.Field()
        class_attrs[f"{node_schema.name}_update"] = update.Field()
        class_attrs[f"{node_schema.name}_delete"] = delete.Field()

    return type("MutationMixin", (object,), class_attrs)


def generate_graphql_object(schema: NodeSchema, branch: Branch) -> Type[InfrahubObject]:
    """Generate a GraphQL object Type from a Infrahub NodeSchema."""

    meta_attrs = {
        "schema": schema,
        "name": schema.kind,
        "description": schema.description,
        "interfaces": set(),
    }

    if schema.inherit_from:
        for generic in schema.inherit_from:
            generic = registry.get_graphql_type(name=generic, branch=branch.name)
            meta_attrs["interfaces"].add(generic)

    main_attrs = {
        "id": graphene.String(required=True),
        "_updated_at": graphene.DateTime(required=False),
        "display_label": graphene.String(required=False),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    for attr in schema.local_attributes:
        if attr.kind not in EXCLUDED_ATTRIBUTE_KINDS:
            attr_type = registry.get_graphql_type(
                name=ATTRIBUTE_TYPES[attr.kind].get_graphql_type_name(), branch=branch.name
            )
            main_attrs[attr.name] = graphene.Field(attr_type, required=not attr.optional, description=attr.description)

    return type(schema.kind, (InfrahubObject,), main_attrs)


def define_relationship_property(branch: Branch, data_source: InfrahubObject, data_owner: InfrahubObject) -> None:
    type_name = "RelationshipProperty"

    meta_attrs = {
        "name": type_name,
        "description": "Defines properties for relationships",
    }

    main_attrs = {
        "is_visible": graphene.Boolean(required=False),
        "is_protected": graphene.Boolean(required=False),
        "updated_at": graphene.DateTime(required=False),
        "source": graphene.Field(data_source),
        "owner": graphene.Field(data_owner),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    relationship_property = type(type_name, (graphene.ObjectType,), main_attrs)

    registry.set_graphql_type(name=type_name, graphql_type=relationship_property, branch=branch.name)


def generate_graphql_edged_object(
    schema: NodeSchema,
    node: Type[InfrahubObject],
    relation_property: Optional[InfrahubObject] = None,
) -> Type[InfrahubObject]:
    """Generate a ednged GraphQL object Type from a Infrahub NodeSchema for pagination."""

    object_name = f"Edged{schema.kind}"
    if relation_property:
        object_name = f"NestedEdged{schema.kind}"

    meta_attrs = {
        "schema": schema,
        "name": object_name,
        "description": schema.description,
        "default_resolver": default_resolver,
        "interfaces": set(),
    }

    main_attrs = {
        "node": graphene.Field(node, required=False),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    if relation_property:
        main_attrs["properties"] = graphene.Field(relation_property)

    return type(object_name, (InfrahubObject,), main_attrs)


def generate_graphql_paginated_object(
    schema: NodeSchema, edge: Type[InfrahubObject], nested: bool = False
) -> Type[InfrahubObject]:
    """Generate a paginated GraphQL object Type from a Infrahub NodeSchema."""

    object_name = f"Paginated{schema.kind}"
    if nested:
        object_name = f"NestedPaginated{schema.kind}"

    meta_attrs = {
        "schema": schema,
        "name": object_name,
        "description": schema.description,
        "default_resolver": default_resolver,
        "interfaces": set(),
    }

    main_attrs = {
        "count": graphene.Int(required=False),
        "has_next": graphene.Boolean(required=False),
        "edges": graphene.List(of_type=edge),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    return type(object_name, (InfrahubObject,), main_attrs)


def generate_union_object(
    schema: GroupSchema,
    members: List,
    branch: Branch,
) -> Type[graphene.Union]:
    types = [registry.get_graphql_type(name=member, branch=branch.name) for member in members]

    if not types:
        return None

    meta_attrs = {
        "schema": schema,
        "name": schema.kind,
        "description": schema.description,
        "types": types,
    }

    main_attrs = {
        "Meta": type("Meta", (object,), meta_attrs),
    }

    return type(schema.kind, (InfrahubUnion,), main_attrs)


def generate_interface_object(schema: GenericSchema, branch: Branch) -> Type[graphene.Interface]:
    meta_attrs = {
        "name": schema.kind,
        "description": schema.description,
    }

    main_attrs = {
        "display_label": graphene.String(required=False),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    for attr in schema.attributes:
        attr_type = registry.get_graphql_type(
            name=ATTRIBUTE_TYPES[attr.kind].get_graphql_type_name(), branch=branch.name
        )
        main_attrs[attr.name] = graphene.Field(attr_type, required=not attr.optional, description=attr.description)

    main_attrs["id"] = graphene.Field(graphene.String, required=False, description="Unique identifier")

    return type(schema.kind, (InfrahubInterface,), main_attrs)


def generate_related_interface_object(
    schema: GenericSchema, branch: Branch, data_source: InfrahubObject, data_owner: InfrahubObject, name_prefix: str
) -> Type[graphene.Interface]:
    meta_attrs = {
        "name": f"{name_prefix}{schema.kind}",
        "description": schema.description,
    }

    main_attrs = {
        "display_label": graphene.String(required=False),
        "_updated_at": graphene.DateTime(required=False),
        "_relation__updated_at": graphene.DateTime(required=False),
        "_relation__is_visible": graphene.Boolean(required=False),
        "_relation__is_protected": graphene.Boolean(required=False),
        "_relation__source": graphene.Field(data_source),
        "_relation__owner": graphene.Field(data_owner),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    for attr in schema.attributes:
        attr_type = registry.get_graphql_type(
            name=ATTRIBUTE_TYPES[attr.kind].get_graphql_type_name(), branch=branch.name
        )
        main_attrs[attr.name] = graphene.Field(attr_type, required=not attr.optional, description=attr.description)

    main_attrs["id"] = graphene.Field(graphene.String, required=False, description="Unique identifier")

    return type(f"{name_prefix}{schema.kind}", (InfrahubInterface,), main_attrs)


def generate_nested_interface_object(
    schema: GenericSchema,
    relation_property: graphene.ObjectType,
    base_interface: graphene.ObjectType,
) -> Type[InfrahubObject]:
    meta_attrs = {
        "name": f"NestedEdged{schema.kind}",
        "schema": schema,
        "description": schema.description,
    }

    main_attrs = {
        "display_label": graphene.String(required=False),
        "node": graphene.Field(base_interface, required=False),
        "_updated_at": graphene.DateTime(required=False),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    if relation_property:
        main_attrs["properties"] = graphene.Field(relation_property)

    return type(f"NestedEdged{schema.kind}", (InfrahubObject,), main_attrs)


def generate_paginated_interface_object(
    schema: GenericSchema,
    base_interface: Type[graphene.ObjectType],
) -> Type[InfrahubObject]:
    meta_attrs = {
        "name": f"NestedPaginated{schema.kind}",
        "schema": schema,
        "description": schema.description,
    }

    main_attrs = {
        "count": graphene.Int(required=False),
        "has_next": graphene.Boolean(required=False),
        "edges": graphene.List(of_type=base_interface),
        "Meta": type("Meta", (object,), meta_attrs),
    }

    return type(f"NestedPaginated{schema.kind}", (InfrahubObject,), main_attrs)


def generate_related_graphql_object(
    schema: NodeSchema, branch: Branch, data_source: InfrahubObject, data_owner: InfrahubObject
) -> Type[InfrahubObject]:
    """Generate a GraphQL object Type from a Infrahub NodeSchema for a Related Node."""

    meta_attrs = {
        "schema": schema,
        "name": f"Related{schema.kind}",
        "description": schema.description,
        "interfaces": {RelatedNodeInterface},
    }

    if schema.inherit_from:
        for generic in schema.inherit_from:
            try:
                generic = registry.get_graphql_type(name=f"Related{generic}", branch=branch.name)
                meta_attrs["interfaces"].add(generic)
            except ValueError:
                # If the object is not present it might be because the generic is a group, will need to carefully test that.
                pass

    main_attrs = {
        "id": graphene.String(required=True),
        "display_label": graphene.String(required=False),
        "_updated_at": graphene.DateTime(required=False),
        "_relation__source": graphene.Field(data_source),
        "_relation__owner": graphene.Field(data_owner),
        "Meta": type("Meta", (object,), meta_attrs),
    }
    for attr in schema.attributes:
        attr_type = registry.get_graphql_type(
            name=ATTRIBUTE_TYPES[attr.kind].get_graphql_type_name(), branch=branch.name
        )
        main_attrs[attr.name] = graphene.Field(attr_type, required=not attr.optional, description=attr.description)

    return type(f"Related{schema.kind}", (InfrahubObject,), main_attrs)


def generate_graphql_mutations(
    schema: NodeSchema, base_class: type[InfrahubMutation], branch: Branch
) -> Tuple[Type[InfrahubMutation], Type[InfrahubMutation], Type[InfrahubMutation]]:
    create = generate_graphql_mutation_create(branch=branch, schema=schema, base_class=base_class)
    update = generate_graphql_mutation_update(branch=branch, schema=schema, base_class=base_class)
    delete = generate_graphql_mutation_delete(branch=branch, schema=schema, base_class=base_class)

    return create, update, delete


def generate_graphql_mutation_create_input(schema: NodeSchema) -> graphene.InputObjectType:
    """Generate an InputObjectType Object from a Infrahub NodeSchema

    Example of Object Generated by this function:
        class StatusCreateInput(InputObjectType):
            id = String(required=False)
            label = InputField(StringAttributeInput, required=True)
            slug = InputField(StringAttributeInput, required=True)
            description = InputField(StringAttributeInput, required=False)
    """
    attrs = {"id": graphene.String(required=False)}

    for attr in schema.attributes:
        attr_type = ATTRIBUTE_TYPES[attr.kind].get_graphql_input()

        # A Field is not required if explicitely indicated or if a default value has been provided
        required = not attr.optional if not attr.default_value else False

        attrs[attr.name] = graphene.InputField(attr_type, required=required, description=attr.description)

    for rel in schema.relationships:
        required = not rel.optional
        if rel.cardinality == "one":
            attrs[rel.name] = graphene.InputField(RelatedNodeInput, required=required, description=rel.description)

        elif rel.cardinality == "many":
            attrs[rel.name] = graphene.InputField(
                graphene.List(RelatedNodeInput), required=required, description=rel.description
            )

    return type(f"{schema.kind}CreateInput", (graphene.InputObjectType,), attrs)


def generate_graphql_mutation_update_input(schema: NodeSchema) -> graphene.InputObjectType:
    """Generate an InputObjectType Object from a Infrahub NodeSchema

    Example of Object Generated by this function:
        class StatusUpdateInput(InputObjectType):
            id = String(required=True)
            label = InputField(StringAttributeInput, required=False)
            slug = InputField(StringAttributeInput, required=False)
            description = InputField(StringAttributeInput, required=False)
    """
    attrs = {"id": graphene.String(required=True)}

    for attr in schema.attributes:
        attr_type = ATTRIBUTE_TYPES[attr.kind].get_graphql_input()
        attrs[attr.name] = graphene.InputField(attr_type, required=False, description=attr.description)

    for rel in schema.relationships:
        if rel.cardinality == "one":
            attrs[rel.name] = graphene.InputField(RelatedNodeInput, required=False, description=rel.description)

        elif rel.cardinality == "many":
            attrs[rel.name] = graphene.InputField(
                graphene.List(RelatedNodeInput), required=False, description=rel.description
            )

    return type(f"{schema.kind}UpdateInput", (graphene.InputObjectType,), attrs)


def generate_graphql_mutation_create(
    schema: NodeSchema,
    branch: Branch,
    base_class: type[InfrahubMutation] = InfrahubMutation,
) -> Type[InfrahubMutation]:
    """Generate a GraphQL Mutation to CREATE an object based on the specified NodeSchema."""
    name = f"{schema.kind}Create"

    object_type = generate_graphql_object(schema=schema, branch=branch)
    input_type = generate_graphql_mutation_create_input(schema=schema)

    main_attrs = {"ok": graphene.Boolean(), "object": graphene.Field(object_type)}

    meta_attrs = {"schema": schema, "name": name, "description": schema.description}
    main_attrs["Meta"] = type("Meta", (object,), meta_attrs)

    args_attrs = {
        "data": input_type(required=True),
    }
    main_attrs["Arguments"] = type("Arguments", (object,), args_attrs)

    return type(name, (base_class,), main_attrs)


def generate_graphql_mutation_update(
    schema: NodeSchema,
    branch: Branch,
    base_class: type[InfrahubMutation] = InfrahubMutation,
) -> Type[InfrahubMutation]:
    """Generate a GraphQL Mutation to UPDATE an object based on the specified NodeSchema."""
    name = f"{schema.kind}Update"

    object_type = generate_graphql_object(schema=schema, branch=branch)
    input_type = generate_graphql_mutation_update_input(schema=schema)

    main_attrs = {"ok": graphene.Boolean(), "object": graphene.Field(object_type)}

    meta_attrs = {"schema": schema, "name": name, "description": schema.description}
    main_attrs["Meta"] = type("Meta", (object,), meta_attrs)

    args_attrs = {
        "data": input_type(required=True),
    }
    main_attrs["Arguments"] = type("Arguments", (object,), args_attrs)

    return type(name, (base_class,), main_attrs)


def generate_graphql_mutation_delete(
    schema: NodeSchema,
    base_class: type[InfrahubMutation] = InfrahubMutation,
    branch: Union[Branch, str] = None,  # pylint: disable=unused-argument
) -> Type[InfrahubMutation]:
    """Generate a GraphQL Mutation to DELETE an object based on the specified NodeSchema."""
    name = f"{schema.kind}Delete"

    main_attrs = {"ok": graphene.Boolean()}

    meta_attrs = {"schema": schema, "name": name, "description": schema.description}
    main_attrs["Meta"] = type("Meta", (object,), meta_attrs)

    args_attrs = {
        "data": DeleteInput(required=True),
    }
    main_attrs["Arguments"] = type("Arguments", (object,), args_attrs)

    return type(name, (base_class,), main_attrs)


async def generate_filters(
    session: AsyncSession, schema: Union[NodeSchema, GenericSchema, GroupSchema], top_level: bool = False
) -> Dict[str, Union[graphene.Scalar, graphene.List]]:
    """Generate the GraphQL filters for a given Schema object.

    The generated filter will be different if we are at the top_level (query)
    or if we are generating the filter for a relationship inside a node.

    At the top, level it will be possible to query with a list of ID
    Inside a node, it's only possible to query with a single ID

    Args:
        session (AsyncSession): Active session to the database
        schema (Union[NodeSchema, GenericSchema, GroupSchema]): Schema to generate the filters
        top_level (bool, optional): Flag to indicate if are at the top level or not. Defaults to False.

    Returns:
        dict: A Dictionnary containing all the filters with their name as the key and their Type as value
    """

    filters: Dict[str, Any] = {"offset": graphene.Int(), "limit": graphene.Int()}
    if top_level:
        filters["ids"] = graphene.List(graphene.ID)
    else:
        filters["id"] = graphene.ID()

    if isinstance(schema, GroupSchema):
        return filters

    for attr in schema.attributes:
        if attr.kind not in EXCLUDED_ATTRIBUTE_KINDS:
            attr_type = ATTRIBUTE_TYPES[attr.kind].graphql_filter
            filters[f"{attr.name}__value"] = attr_type()

    if not top_level:
        return filters

    for rel in schema.relationships:
        peer_schema = await rel.get_peer_schema()

        if not isinstance(peer_schema, NodeSchema):
            continue

        peer_filters = await generate_filters(session=session, schema=peer_schema, top_level=False)

        for key, value in peer_filters.items():
            filters[f"{rel.name}__{key}"] = value

    return filters
