import pytest
from pydantic.error_wrappers import ValidationError

from infrahub.core import registry
from infrahub.core.schema import NodeSchema, SchemaRoot, core_models, internal_schema


def test_schema_root_no_generic():
    FULL_SCHEMA = {
        "nodes": [
            {
                "name": "criticality",
                "kind": "Criticality",
                "default_filter": "name__value",
                "branch": True,
                "attributes": [
                    {"name": "name", "kind": "String", "unique": True},
                ],
            }
        ]
    }

    assert SchemaRoot(**FULL_SCHEMA)


def test_node_schema_unique_names():
    SCHEMA = {
        "name": "criticality",
        "kind": "Criticality",
        "default_filter": "name__value",
        "branch": True,
        "attributes": [
            {"name": "name", "kind": "String", "unique": True},
            {"name": "name", "kind": "String", "unique": True},
        ],
    }

    with pytest.raises(ValidationError) as exc:
        NodeSchema(**SCHEMA)

    assert "Names of attributes and relationships must be unique" in str(exc.value)

    SCHEMA = {
        "name": "criticality",
        "kind": "Criticality",
        "default_filter": "name__value",
        "branch": True,
        "attributes": [
            {"name": "name", "kind": "String", "unique": True},
            {"name": "dupname", "kind": "String"},
        ],
        "relationships": [
            {"name": "dupname", "peer": "Criticality", "cardinality": "one"},
        ],
    }

    with pytest.raises(ValidationError) as exc:
        NodeSchema(**SCHEMA)

    assert "Names of attributes and relationships must be unique" in str(exc.value)


def test_node_schema_unique_identifiers():
    SCHEMA = {
        "name": "criticality",
        "kind": "Criticality",
        "default_filter": "name__value",
        "branch": True,
        "attributes": [
            {"name": "name", "kind": "String", "unique": True},
        ],
        "relationships": [
            {"name": "first", "peer": "Criticality", "cardinality": "one"},
            {"name": "second", "peer": "Criticality", "cardinality": "one"},
        ],
    }

    with pytest.raises(ValidationError) as exc:
        schema = NodeSchema(**SCHEMA)

    assert "Identifier of relationships must be unique" in str(exc.value)

    SCHEMA = {
        "name": "criticality",
        "kind": "Criticality",
        "default_filter": "name__value",
        "branch": True,
        "attributes": [
            {"name": "name", "kind": "String", "unique": True},
        ],
        "relationships": [
            {"name": "first", "peer": "Criticality", "cardinality": "one"},
            {"name": "second", "identifier": "something_unique", "peer": "Criticality", "cardinality": "one"},
        ],
    }
    schema = NodeSchema(**SCHEMA)
    assert schema.relationships[0].identifier == "criticality__criticality"
    assert schema.relationships[1].identifier == "something_unique"


async def test_rel_schema_query_filter(session, default_branch, car_person_schema):
    person = registry.get_schema(name="Person")
    rel = person.relationships[0]

    filters, params, nbr_rels = await rel.get_query_filter(session=session)
    assert filters == []
    assert params == {}
    assert nbr_rels == 0

    # Filter relationships by NAME__VALUE
    filters, params, nbr_rels = await rel.get_query_filter(session=session, filters={"name__value": "alice"})
    expected_response = [
        "MATCH (n)-[r1:IS_RELATED]-(rl:Relationship { name: $rel_cars_rel_name })-[r2:IS_RELATED]-(p:Car)-[r3:HAS_ATTRIBUTE]-(i:Attribute { name: $attr_name_name } )-[r4:HAS_VALUE]-(av { value: $attr_name_value })"
    ]
    assert filters == expected_response
    assert params == {"attr_name_name": "name", "attr_name_value": "alice", "rel_cars_rel_name": "car__person"}
    assert nbr_rels == 4

    # Filter relationship by ID
    filters, params, nbr_rels = await rel.get_query_filter(session=session, name="bob", filters={"id": "XXXX-YYYY"})
    expected_response = [
        "MATCH (n)-[r1:IS_RELATED]-(Relationship { name: $rel_cars_rel_name })-[r2:IS_RELATED]-(p:Car { uuid: $peer_node_id })"
    ]
    assert filters == expected_response
    assert params == {"peer_node_id": "XXXX-YYYY", "rel_cars_rel_name": "car__person"}
    assert nbr_rels == 2


async def test_extend_node_with_interface(session, default_branch):
    SCHEMA = {
        "generics": [
            {
                "name": "generic_interface",
                "kind": "GenericInterface",
                "branch": True,
                "attributes": [
                    {"name": "my_generic_name", "kind": "String"},
                ],
            }
        ],
        "nodes": [
            {
                "name": "mynode",
                "kind": "MYNode",
                "default_filter": "name__value",
                "inherit_from": ["GenericInterface"],
                "branch": True,
                "attributes": [
                    {"name": "name", "kind": "String", "unique": True},
                    {"name": "description", "kind": "String", "optional": True},
                ],
            }
        ],
    }
    schema = SchemaRoot(**SCHEMA)
    schema.extend_nodes_with_interfaces()

    assert "my_generic_name" in schema.nodes[0].valid_input_names
    assert schema.nodes[0].get_attribute("my_generic_name").inherited


def test_core_models():
    assert SchemaRoot(**core_models)


def test_internal_schema():
    assert SchemaRoot(**internal_schema)
