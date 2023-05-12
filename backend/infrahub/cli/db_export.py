import json
import logging
from asyncio import run as aiorun
from pathlib import Path
from typing import List, Optional

import typer
from pydantic import BaseModel

import infrahub.config as config
from infrahub.database import execute_read_query_async, get_db

NODE_PROPERTIES_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
WITH label AS nodeLabels, collect(property) AS properties
RETURN {labels: nodeLabels, properties: properties} AS output
"""

REL_PROPERTIES_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "relationship"
WITH label AS nodeLabels, collect(property) AS properties
RETURN {type: nodeLabels, properties: properties} AS output
"""

REL_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE type = "RELATIONSHIP" AND elementType = "node"
RETURN {source: label, relationship: property, target: other} AS output
"""

app = typer.Typer()


class InternalSchemaNode(BaseModel):
    label: str
    properties: List[str]


class InternalSchemaRelationship(BaseModel):
    type: str
    properties: List[str]


class InternalSchemaRelationship2(BaseModel):
    source: str
    destination: List[str]
    relationship: str


class InternalSchema(BaseModel):
    nodes: List[InternalSchemaNode]
    relationships: List[InternalSchemaRelationship]
    relationships2: List[InternalSchemaRelationship2]


@app.callback()
def callback():
    """
    Export various information from the database
    """


async def _export_internal_schema(output_file: Path):
    """Export the internal schema in json format."""

    db = await get_db(retry=1)

    async with db.session(database=config.SETTINGS.database.database) as session:
        results = await execute_read_query_async(session=session, query=NODE_PROPERTIES_QUERY)
        nodes_result = [{"label": result[0]["labels"], "properties": result[0]["properties"]} for result in results]

        results = await execute_read_query_async(session=session, query=REL_PROPERTIES_QUERY)
        rels_result = [{"type": result[0]["type"], "properties": result[0]["properties"]} for result in results]

        results = await execute_read_query_async(session=session, query=REL_QUERY)
        rels_result2 = [
            {
                "source": result[0]["source"],
                "destination": result[0]["target"],
                "relationship": result[0]["relationship"],
            }
            for result in results
        ]

    schema = InternalSchema(nodes=nodes_result, relationships=rels_result, relationships2=rels_result2)

    schema_str = json.dumps(schema.dict(), indent=4, sort_keys=True)
    output_file.write_text(schema_str, encoding="utf-8")


@app.command()
def internal_schema(
    config_file: str = typer.Argument("infrahub.toml", envvar="INFRAHUB_CONFIG"),
    out: Optional[Path] = typer.Argument("infrahub_schema.json"),
):
    """Export the internal schema in json format."""

    logging.getLogger("neo4j").setLevel(logging.ERROR)
    config.load_and_exit(config_file_name=config_file)

    aiorun(_export_internal_schema(output_file=out))


async def _export_data(output_file: Path):
    """Export the internal schema in json format."""

    query = """
    CALL apoc.export.csv.all(null, {stream:true})
    YIELD file, nodes, relationships, properties, data
    RETURN file, nodes, relationships, properties, data
    """
    db = await get_db(retry=1)

    async with db.session(database=config.SETTINGS.database.database) as session:
        results = await execute_read_query_async(session=session, query=query)

    # print(results)
    # schema = InternalSchema(nodes=nodes_result, relationships=rels_result, relationships2=rels_result2)

    # schema_str = json.dumps(schema.dict(), indent=4, sort_keys=True)
    output_file.write_text(results[0][4], encoding="utf-8")


@app.command()
def data(
    config_file: str = typer.Argument("infrahub.toml", envvar="INFRAHUB_CONFIG"),
    out: Optional[Path] = typer.Argument("infrahub_dump.csv"),
):
    """Export the content of the database in CSV format."""

    logging.getLogger("neo4j").setLevel(logging.ERROR)
    config.load_and_exit(config_file_name=config_file)

    aiorun(_export_data(output_file=out))
