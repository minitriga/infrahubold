from deepdiff import DeepDiff

from infrahub.core import registry
from infrahub.core.manager import SchemaManager
from infrahub.core.schema import (
    GenericSchema,
    GroupSchema,
    NodeSchema,
    SchemaRoot,
    core_models,
    internal_schema,
)


async def test_register_schema_to_registry(session, default_branch):
    FULL_SCHEMA = {
        "nodes": [
            {
                "name": "criticality",
                "kind": "Criticality",
                "default_filter": "name__value",
                "branch": True,
                "attributes": [
                    {"name": "name", "kind": "String", "unique": True},
                    {"name": "level", "kind": "Integer"},
                    {"name": "color", "kind": "String", "default_value": "#444444"},
                    {"name": "description", "kind": "String", "optional": True},
                ],
            }
        ],
        "generics": [
            {
                "name": "generic_interface",
                "kind": "GenericInterface",
                "branch": True,
                "attributes": [
                    {"name": "my_generic_name", "kind": "String"},
                ],
            },
        ],
        "groups": [
            {
                "name": "generic_group",
                "kind": "GenericGroup",
            },
        ],
    }
    schema = SchemaRoot(**FULL_SCHEMA)
    await SchemaManager.register_schema_to_registry(schema=schema)

    assert isinstance(registry.get_schema(name="Criticality"), NodeSchema)
    assert isinstance(registry.get_schema(name="GenericGroup"), GroupSchema)
    assert isinstance(registry.get_schema(name="GenericInterface"), GenericSchema)


async def test_load_node_to_db_node_schema(session, default_branch):
    schema = SchemaRoot(**internal_schema)
    await SchemaManager.register_schema_to_registry(schema=schema)

    SCHEMA = {
        "name": "criticality",
        "kind": "Criticality",
        "default_filter": "name__value",
        "branch": True,
        "attributes": [
            {"name": "name", "kind": "String", "unique": True},
            {"name": "level", "kind": "Integer"},
            {"name": "color", "kind": "String", "default_value": "#444444"},
            {"name": "description", "kind": "String", "optional": True},
        ],
    }
    node = NodeSchema(**SCHEMA)
    await SchemaManager.load_node_to_db(node=node, session=session)

    assert True


async def test_load_node_to_db_generic_schema(session, default_branch):
    schema = SchemaRoot(**internal_schema)
    await SchemaManager.register_schema_to_registry(schema=schema)

    SCHEMA = {
        "name": "generic_interface",
        "kind": "GenericInterface",
        "branch": True,
        "attributes": [
            {"name": "my_generic_name", "kind": "String"},
        ],
    }
    node = GenericSchema(**SCHEMA)
    await SchemaManager.load_node_to_db(node=node, session=session)

    assert True


async def test_load_node_to_db_group_schema(session, default_branch):
    schema = SchemaRoot(**internal_schema)
    await SchemaManager.register_schema_to_registry(schema=schema)

    SCHEMA = {
        "name": "generic_group",
        "kind": "GenericGroup",
    }

    node = GroupSchema(**SCHEMA)
    await SchemaManager.load_node_to_db(node=node, session=session)

    assert True


async def test_load_schema_to_db_internal_models(session, default_branch):
    schema = SchemaRoot(**internal_schema)
    await SchemaManager.register_schema_to_registry(schema=schema)

    await SchemaManager.load_schema_to_db(schema=schema, session=session)

    node_schema = registry.get_schema(name="NodeSchema")
    results = await SchemaManager.query(schema=node_schema, session=session)
    assert len(results) > 1


async def test_load_schema_to_db_core_models(session, default_branch, register_internal_models_schema):
    schema = SchemaRoot(**core_models)
    await SchemaManager.register_schema_to_registry(schema=schema)

    await SchemaManager.load_schema_to_db(schema=schema, session=session)

    node_schema = registry.get_schema(name="GenericSchema")
    results = await SchemaManager.query(schema=node_schema, session=session)
    assert len(results) > 1


async def test_load_schema_from_db(session, reset_registry, default_branch, register_internal_models_schema):
    FULL_SCHEMA = {
        "nodes": [
            {
                "name": "criticality",
                "kind": "Criticality",
                "default_filter": "name__value",
                "branch": True,
                "attributes": [
                    {"name": "name", "kind": "String", "unique": True},
                    {"name": "level", "kind": "Integer"},
                    {"name": "color", "kind": "String", "default_value": "#444444"},
                    {"name": "description", "kind": "String", "optional": True},
                ],
                "relationships": [
                    {"name": "tags", "peer": "Tag", "optional": True, "cardinality": "many"},
                    {
                        "name": "primary_tag",
                        "peer": "Tag",
                        "identifier": "primary_tag__criticality",
                        "optional": True,
                        "cardinality": "one",
                    },
                ],
            },
            {
                "name": "tag",
                "kind": "Tag",
                "default_filter": "name__value",
                "branch": True,
                "attributes": [
                    {"name": "name", "kind": "String", "unique": True},
                    {"name": "description", "kind": "String", "optional": True},
                ],
            },
        ],
        "generics": [
            {
                "name": "generic_interface",
                "kind": "GenericInterface",
                "branch": True,
                "attributes": [
                    {"name": "my_generic_name", "kind": "String"},
                ],
            },
        ],
        "groups": [
            {
                "name": "generic_group",
                "kind": "GenericGroup",
            },
        ],
    }
    schema1 = SchemaRoot(**FULL_SCHEMA)
    await SchemaManager.load_schema_to_db(schema=schema1, session=session)

    schema2 = await SchemaManager.load_schema_from_db(session=session)

    assert len(schema2.nodes) == 2
    assert len(schema2.generics) == 1
    assert len(schema2.groups) == 1

    schema_criticality = [node for node in schema2.nodes if node.kind == "Criticality"][0]

    # breakpoint()
    assert not DeepDiff(
        schema1.nodes[0].dict(exclude={"filters", "relationships"}),
        schema_criticality.dict(exclude={"filters", "relationships"}),
        ignore_order=True,
    )
    assert not DeepDiff(
        schema1.generics[0].dict(exclude={"filters"}), schema2.generics[0].dict(exclude={"filters"}), ignore_order=True
    )
    assert not DeepDiff(
        schema1.groups[0].dict(exclude={"filters"}), schema2.groups[0].dict(exclude={"filters"}), ignore_order=True
    )

    criticality_dict = schema_criticality.dict()

    expected_filters = [
        {"name": "ids", "kind": "List", "description": None},
        {"name": "level__value", "kind": "Integer", "description": None},
        {"name": "color__value", "kind": "String", "description": None},
        {"name": "name__value", "kind": "String", "description": None},
        {"name": "description__value", "kind": "String", "description": None},
    ]

    expected_relationships = [
        {
            "name": "tags",
            "peer": "Tag",
            "label": None,
            "description": None,
            "identifier": "criticality__tag",
            "inherited": False,
            "cardinality": "many",
            "branch": True,
            "optional": True,
            "filters": [
                {"name": "id", "kind": "String", "description": None},
                {"name": "description__value", "kind": "String", "description": None},
                {"name": "name__value", "kind": "String", "description": None},
            ],
        },
        {
            "name": "primary_tag",
            "peer": "Tag",
            "label": None,
            "description": None,
            "identifier": "primary_tag__criticality",
            "inherited": False,
            "cardinality": "one",
            "branch": True,
            "optional": True,
            "filters": [
                {"name": "id", "kind": "String", "description": None},
                {"name": "description__value", "kind": "String", "description": None},
                {"name": "name__value", "kind": "String", "description": None},
            ],
        },
    ]

    assert not DeepDiff(criticality_dict["filters"], expected_filters, ignore_order=True)

    assert not DeepDiff(criticality_dict["relationships"], expected_relationships, ignore_order=True)
