from infrahub.core import registry
from infrahub.core.branch import Branch
from infrahub.core.constants import PathResourceType, PathType, SchemaPathType
from infrahub.core.node import Node
from infrahub.core.path import DataPath, SchemaPath
from infrahub.core.validators.attribute.unique import (
    AttributeUniqueUpdateValidator,
    AttributeUniqueUpdateValidatorQuery,
)
from infrahub.database import InfrahubDatabase


async def test_query(
    db: InfrahubDatabase,
    branch: Branch,
    default_branch: Branch,
    car_accord_main: Node,
    car_prius_main: Node,
    car_yaris_main: Node,
    car_volt_main: Node,
    person_john_main,
):
    await branch.rebase(db=db)
    car = await Node.init(db=db, schema="TestCar", branch=branch)
    await car.new(db=db, name="New Accord", nbr_seats=5, is_electric=False, owner=person_john_main.id)
    await car.save(db=db)

    car_schema = registry.schema.get(name="TestCar")
    seats_attr = car_schema.get_attribute(name="nbr_seats")
    seats_attr.unique = True

    node_schema = car_schema
    schema_path = SchemaPath(path_type=SchemaPathType.ATTRIBUTE, schema_kind="TestCar", field_name="nbr_seats")
    query = await AttributeUniqueUpdateValidatorQuery.init(
        db=db, branch=branch, node_schema=node_schema, schema_path=schema_path
    )

    await query.execute(db=db)

    grouped_paths = await query.get_paths()
    assert len(grouped_paths.get_data_paths(5)) == 3

    assert DataPath(
        resource_type=PathResourceType.DATA,
        branch=branch.name,
        path_type=PathType.ATTRIBUTE,
        node_id=car.id,
        kind="TestCar",
        field_name="nbr_seats",
        value=5,
    ) in grouped_paths.get_data_paths(5)
    assert DataPath(
        resource_type=PathResourceType.DATA,
        branch=default_branch.name,
        path_type=PathType.ATTRIBUTE,
        node_id=car_accord_main.id,
        kind="TestCar",
        field_name="nbr_seats",
        value=5,
    ) in grouped_paths.get_data_paths(5)
    assert DataPath(
        resource_type=PathResourceType.DATA,
        branch=default_branch.name,
        path_type=PathType.ATTRIBUTE,
        node_id=car_prius_main.id,
        kind="TestCar",
        field_name="nbr_seats",
        value=5,
    ) in grouped_paths.get_data_paths(5)
    assert len(grouped_paths.get_data_paths(4)) == 2
    assert {dp.node_id for dp in grouped_paths.get_data_paths(4)} == {car_yaris_main.id, car_volt_main.id}


async def test_validator(
    db: InfrahubDatabase,
    branch: Branch,
    car_accord_main: Node,
    car_prius_main: Node,
    car_yaris_main: Node,
    car_volt_main: Node,
    person_john_main,
):
    await branch.rebase(db=db)
    car = await Node.init(db=db, schema="TestCar", branch=branch)
    await car.new(db=db, name="New Accord", nbr_seats=5, is_electric=False, owner=person_john_main.id)
    await car.save(db=db)

    car_schema = registry.schema.get(name="TestCar")
    seats_attr = car_schema.get_attribute(name="nbr_seats")
    seats_attr.unique = True

    validator = AttributeUniqueUpdateValidator(
        node_schema=car_schema,
        schema_path=SchemaPath(path_type=SchemaPathType.ATTRIBUTE, schema_kind="TestCar", field_name="nbr_seats"),
    )
    violations = await validator.run_validate(db=db, branch=branch)

    assert len(violations) == 5
    assert {v.node_id for v in violations} == {
        car.id,
        car_accord_main.id,
        car_prius_main.id,
        car_yaris_main.id,
        car_volt_main.id,
    }