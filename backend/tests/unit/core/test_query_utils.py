from infrahub.core import registry
from infrahub.core.branch import Branch
from infrahub.core.query.utils import build_subquery_filter, build_subquery_order
from infrahub.core.schema import NodeSchema


async def test_build_subquery_filter_attribute_text(
    session, default_branch: Branch, all_attribute_types_schema: NodeSchema
):
    attr_schema = all_attribute_types_schema.get_attribute(name="mystring")

    query, params, result_name = await build_subquery_filter(
        session=session,
        field=attr_schema,
        name="name",
        filter_name="value",
        filter_value="myname",
        branch_filter="PLACEHOLDER",
        branch=default_branch,
        subquery_idx=1,
    )

    expected_query = """
    WITH n
    MATCH p = (n)-[f1r1:HAS_ATTRIBUTE]-(i:Attribute { name: $filter1_name })-[f1r2:HAS_VALUE]-(av:AttributeValue { value: $filter1_value })
    WHERE all(r IN relationships(p) WHERE (PLACEHOLDER))
    RETURN n as filter1
    ORDER BY [ f1r1.from, f1r2.from ]
    LIMIT 1
    """
    assert query == expected_query
    assert params == {"filter1_name": "name", "filter1_value": "myname"}
    assert result_name == "filter1"


async def test_build_subquery_filter_attribute_int(
    session, default_branch: Branch, all_attribute_types_schema: NodeSchema
):
    attr_schema = all_attribute_types_schema.get_attribute(name="myint")

    query, params, result_name = await build_subquery_filter(
        session=session,
        field=attr_schema,
        name="name",
        filter_name="value",
        filter_value=5,
        branch_filter="PLACEHOLDER",
        branch=default_branch,
        subquery_idx=2,
    )

    expected_query = """
    WITH n
    MATCH p = (n)-[f2r1:HAS_ATTRIBUTE]-(i:Attribute { name: $filter2_name })-[f2r2:HAS_VALUE]-(av:AttributeValue { value: $filter2_value })
    WHERE all(r IN relationships(p) WHERE (PLACEHOLDER))
    RETURN n as filter2
    ORDER BY [ f2r1.from, f2r2.from ]
    LIMIT 1
    """
    assert query == expected_query
    assert params == {"filter2_name": "name", "filter2_value": 5}
    assert result_name == "filter2"


async def test_build_subquery_filter_relationship(session, default_branch: Branch, car_person_schema):
    car_schema = registry.schema.get(name="Car")
    rel_schema = car_schema.get_relationship(name="owner")

    query, params, result_name = await build_subquery_filter(
        session=session,
        field=rel_schema,
        name="owner",
        filter_name="name__value",
        filter_value="john",
        branch_filter="PLACEHOLDER",
        branch=default_branch,
        subquery_idx=1,
    )

    # ruff: noqa: E501
    expected_query = """
    WITH n
    MATCH p = (n)-[f1r1:IS_RELATED]-(rl:Relationship { name: $filter1_rel_name })-[f1r2:IS_RELATED]-(peer:Node)-[f1r3:HAS_ATTRIBUTE]-(i:Attribute { name: $filter1_name })-[f1r4:HAS_VALUE]-(av:AttributeValue { value: $filter1_value })
    WHERE all(r IN relationships(p) WHERE (PLACEHOLDER))
    RETURN n as filter1
    ORDER BY [ f1r1.from, f1r2.from, f1r3.from, f1r4.from ]
    LIMIT 1
    """
    assert query == expected_query
    assert params == {
        "filter1_name": "name",
        "filter1_rel_name": "car__person",
        "filter1_value": "john",
    }
    assert result_name == "filter1"


async def test_build_subquery_order_relationship(session, default_branch: Branch, car_person_schema):
    car_schema = registry.schema.get(name="Car")
    rel_schema = car_schema.get_relationship(name="owner")

    query, params, result_name = await build_subquery_order(
        session=session,
        field=rel_schema,
        name="owner",
        order_by="name__value",
        branch_filter="PLACEHOLDER",
        branch=default_branch,
        subquery_idx=1,
    )

    expected_query = """
    WITH n
    MATCH p = (n)-[ord1r1:IS_RELATED]-(:Relationship { name: $order1_rel_name })-[ord1r2:IS_RELATED]-(:Node)-[ord1r3:HAS_ATTRIBUTE]-(:Attribute { name: $order1_name })-[ord1r4:HAS_VALUE]-(last:AttributeValue)
    WHERE all(r IN relationships(p) WHERE (PLACEHOLDER))
    RETURN last.value as order1
    ORDER BY [ ord1r1.from, ord1r2.from, ord1r3.from, ord1r4.from ]
    LIMIT 1
    """
    assert query == expected_query
    assert params == {"order1_name": "name", "order1_rel_name": "car__person"}
    assert result_name == "order1"
