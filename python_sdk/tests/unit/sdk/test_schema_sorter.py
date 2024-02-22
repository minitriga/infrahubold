
from infrahub_sdk import InfrahubClient
from infrahub_sdk.schema_sorter import InfrahubSchemaTopologicalSorter


async def test_schema_sorter(client: InfrahubClient, mock_schema_query_06):

    schemas = await client.schema.all()
    include = ["BuiltinLocation", "InfraDevice", "InfraInterfaceL2", "InfraInterfaceL3"]
    result = InfrahubSchemaTopologicalSorter.get_sorted_node_schema(schemas=schemas.values(), include=include)
    assert result == []