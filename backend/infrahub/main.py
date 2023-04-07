import copy
import logging
import os
import time
from typing import List, Optional

import graphene
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.logger import logger
from graphql import graphql
from neo4j import AsyncSession
from pydantic import BaseModel
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from starlette_exporter import PrometheusMiddleware, handle_metrics

import infrahub.config as config
from infrahub import __version__
from infrahub.auth import BaseTokenAuth
from infrahub.config import AnalyticsSettings, LoggingSettings, MainSettings
from infrahub.core import get_branch, registry
from infrahub.core.initialization import initialization
from infrahub.core.manager import NodeManager, SchemaManager
from infrahub.core.schema import GenericSchema, NodeSchema, SchemaRoot
from infrahub.database import get_db
from infrahub.exceptions import BranchNotFound
from infrahub.graphql import get_gql_mutation, get_gql_query
from infrahub.graphql.app import InfrahubGraphQLApp
from infrahub.message_bus import close_broker_connection, connect_to_broker
from infrahub.message_bus.events import (
    InfrahubRPCResponse,
    InfrahubTransformRPC,
    RPCStatusCode,
    TransformMessageAction,
)
from infrahub.message_bus.rpc import InfrahubRpcClient
from infrahub.middleware import InfrahubCORSMiddleware
from infrahub_client.timestamp import Timestamp

app = FastAPI(
    title="Infrahub",
    version="0.2.0",
    contact={
        "name": "OpsMill",
        "email": "info@opsmill.com",
    },
)

# pylint: disable=too-many-locals

gunicorn_logger = logging.getLogger("gunicorn.error")
logger.handlers = gunicorn_logger.handlers


async def get_session(request: Request) -> AsyncSession:
    session = request.app.state.db.session(database=config.SETTINGS.database.database)
    try:
        yield session
    finally:
        await session.close()


@app.on_event("startup")
async def app_initialization():
    if not config.SETTINGS:
        config_file_name = os.environ.get("INFRAHUB_CONFIG", "infrahub.toml")
        config_file_path = os.path.abspath(config_file_name)
        logger.info(f"Loading the configuration from {config_file_path}")
        config.load_and_exit(config_file_path)

    # Initialize database Driver and load local registry
    app.state.db = await get_db()

    async with app.state.db.session(database=config.SETTINGS.database.database) as session:
        await initialization(session=session)

    # Initialize connection to the RabbitMQ bus
    await connect_to_broker()

    # Initialize RPC Client
    app.state.rpc_client = await InfrahubRpcClient().connect()


@app.on_event("shutdown")
async def shutdown():
    await close_broker_connection()
    await app.state.db.close()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


class SchemaReadAPI(BaseModel):
    nodes: List[NodeSchema]
    generics: List[GenericSchema]


@app.get("/schema/")
async def get_schema(
    session: AsyncSession = Depends(get_session),
    branch: Optional[str] = None,
) -> SchemaReadAPI:
    try:
        branch = await get_branch(session=session, branch=branch)
    except BranchNotFound as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    # Make a local copy of the schema to ensure that any modification won't touch the objects in the registry
    full_schema = copy.deepcopy(registry.get_full_schema(branch=branch))

    # Populate the used_by field on all the generics objects
    # ideally we should populate this value directly in the registry
    # but this will require a bigger refactoring so for now it's best to do it here
    for kind, item in full_schema.items():
        if not isinstance(item, NodeSchema):
            continue

        for generic in item.inherit_from:
            if generic not in full_schema:
                logger.warning(f"Unable to find the Generic Object {generic}, referenced by {kind}")
                continue
            if kind not in full_schema[generic].used_by:
                full_schema[generic].used_by.append(kind)

    return SchemaReadAPI(
        nodes=[value for value in full_schema.values() if isinstance(value, NodeSchema)],
        generics=[value for value in full_schema.values() if isinstance(value, GenericSchema)],
    )


class SchemaLoadAPI(SchemaRoot):
    version: str


@app.post("/schema/load/")
async def load_schema(
    schema: SchemaLoadAPI,
    session: AsyncSession = Depends(get_session),
    branch: Optional[str] = None,
):
    try:
        branch = await get_branch(session=session, branch=branch)
    except BranchNotFound as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    schema.extend_nodes_with_interfaces()
    await SchemaManager.register_schema_to_registry(schema)
    await SchemaManager.load_schema_to_db(schema, session=session)

    return JSONResponse(status_code=202, content={})


class ConfigAPI(BaseModel):
    main: MainSettings
    logging: LoggingSettings
    analytics: AnalyticsSettings


@app.get("/config/")
async def get_config() -> ConfigAPI:
    return ConfigAPI(main=config.SETTINGS.main, logging=config.SETTINGS.logging, analytics=config.SETTINGS.analytics)


class InfoAPI(BaseModel):
    deployment_id: str
    version: str


@app.get("/info/")
async def get_info() -> InfoAPI:
    return InfoAPI(deployment_id=str(registry.id), version=__version__)


@app.get("/rfile/{rfile_id}", response_class=PlainTextResponse)
async def generate_rfile(
    request: Request,
    rfile_id: str,
    session: AsyncSession = Depends(get_session),
    branch: Optional[str] = None,
    at: Optional[str] = None,
    rebase: Optional[bool] = False,
):
    try:
        branch = await get_branch(session=session, branch=branch)
    except BranchNotFound as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    branch.ephemeral_rebase = rebase
    at = Timestamp(at)

    params = {key: value for key, value in request.query_params.items() if key not in ["branch", "rebase", "at"]}

    rfile = await NodeManager.get_one(session=session, id=rfile_id, branch=branch, at=at)

    if not rfile:
        rfile_schema = registry.get_schema(name="RFile", branch=branch)
        items = await NodeManager.query(
            session=session, schema=rfile_schema, filters={rfile_schema.default_filter: rfile_id}, branch=branch, at=at
        )
        if items:
            rfile = items[0]

    if not rfile:
        raise HTTPException(status_code=404, detail="Item not found")

    query = await rfile.query.get_peer(session=session)
    repository = await rfile.template_repository.get_peer(session=session)

    result = await graphql(
        graphene.Schema(
            query=await get_gql_query(session=session, branch=branch),
            mutation=await get_gql_mutation(session=session, branch=branch),
            auto_camelcase=False,
        ).graphql_schema,
        source=query.query.value,
        context_value={
            "infrahub_branch": branch,
            "infrahub_at": at,
            "infrahub_database": request.app.state.db,
            "infrahub_session": session,
        },
        root_value=None,
        variable_values=params,
    )

    if result.errors:
        errors = []
        for error in result.errors:
            errors.append(
                {
                    "message": f"GraphQLQuery {query.name.value}: {error.message}",
                    "path": error.path,
                    "locations": [{"line": location.line, "column": location.column} for location in error.locations],
                }
            )

        return JSONResponse(status_code=500, content={"errors": errors})

    rpc_client: InfrahubRpcClient = request.app.state.rpc_client

    response: InfrahubRPCResponse = await rpc_client.call(
        message=InfrahubTransformRPC(
            action=TransformMessageAction.JINJA2,
            repository=repository,
            data=result.data,
            branch_name=branch.name,
            transform_location=rfile.template_path.value,
        )
    )

    if response.status == RPCStatusCode.OK.value:
        return response.response["rendered_template"]

    return JSONResponse(status_code=response.status, content={"errors": response.errors})


@app.get("/query/{query_id}")
async def graphql_query(
    request: Request,
    response: Response,
    query_id: str,
    session: AsyncSession = Depends(get_session),
    branch: Optional[str] = None,
    at: Optional[str] = None,
    rebase: bool = False,
):
    try:
        branch = await get_branch(session=session, branch=branch)
    except BranchNotFound as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    branch.ephemeral_rebase = rebase
    at = Timestamp(at)

    params = {key: value for key, value in request.query_params.items() if key not in ["branch", "rebase", "at"]}

    gql_query = await NodeManager.get_one(session=session, id=query_id, branch=branch, at=at)

    if not gql_query:
        gqlquery_schema = registry.get_schema(name="GraphQLQuery", branch=branch)
        items = await NodeManager.query(
            session=session,
            schema=gqlquery_schema,
            filters={gqlquery_schema.default_filter: query_id},
            branch=branch,
            at=at,
        )
        if items:
            gql_query = items[0]

    if not gql_query:
        raise HTTPException(status_code=404, detail="Item not found")

    result = await graphql(
        graphene.Schema(
            query=await get_gql_query(session=session, branch=branch),
            mutation=await get_gql_mutation(session=session, branch=branch),
            auto_camelcase=False,
        ).graphql_schema,
        source=gql_query.query.value,
        context_value={
            "infrahub_branch": branch,
            "infrahub_at": at,
            "infrahub_database": request.app.state.db,
            "infrahub_session": session,
        },
        root_value=None,
        variable_values=params,
    )

    response_payload = {"data": result.data}

    if result.errors:
        response_payload["errors"] = []
        for error in result.errors:
            response_payload["errors"].append(
                {
                    "message": error.message,
                    "path": error.path,
                    "locations": [{"line": location.line, "column": location.column} for location in error.locations],
                }
            )
        response.status_code = 500

    return response_payload


@app.get("/transform/{transform_url:path}")
async def transform_python(
    request: Request,
    transform_url: str,
    session: AsyncSession = Depends(get_session),
    branch: Optional[str] = None,
    at: Optional[str] = None,
    rebase: Optional[bool] = False,
):
    try:
        branch = await get_branch(session=session, branch=branch)
    except BranchNotFound as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    branch.ephemeral_rebase = rebase
    at = Timestamp(at)

    params = {key: value for key, value in request.query_params.items() if key not in ["branch", "rebase", "at"]}

    transform_schema = registry.get_schema(name="TransformPython", branch=branch)
    transforms = await NodeManager.query(
        session=session, schema=transform_schema, filters={"url__value": transform_url}, branch=branch, at=at
    )

    if not transforms:
        raise HTTPException(status_code=404, detail="Item not found")

    transform = transforms[0]

    query = await transform.query.get_peer(session=session)
    repository = await transform.repository.get_peer(session=session)

    result = await graphql(
        graphene.Schema(
            query=await get_gql_query(session=session, branch=branch),
            mutation=await get_gql_mutation(session=session, branch=branch),
            auto_camelcase=False,
        ).graphql_schema,
        source=query.query.value,
        context_value={
            "infrahub_branch": branch,
            "infrahub_at": at,
            "infrahub_database": request.app.state.db,
            "infrahub_session": session,
        },
        root_value=None,
        variable_values=params,
    )

    if result.errors:
        errors = []
        for error in result.errors:
            errors.append(
                {
                    "message": f"GraphQLQuery {query.name.value}: {error.message}",
                    "path": error.path,
                    "locations": [{"line": location.line, "column": location.column} for location in error.locations],
                }
            )

        return JSONResponse(status_code=500, content={"errors": errors})

    rpc_client: InfrahubRpcClient = request.app.state.rpc_client

    response: InfrahubRPCResponse = await rpc_client.call(
        message=InfrahubTransformRPC(
            action=TransformMessageAction.PYTHON,
            repository=repository,
            data=result.data,
            branch_name=branch.name,
            transform_location=f"{transform.file_path.value}::{transform.class_name.value}",
        )
    )

    if response.status == RPCStatusCode.OK.value:
        return response.response["transformed_data"]

    return JSONResponse(status_code=response.status, content={"errors": response.errors})


app.add_middleware(
    AuthenticationMiddleware,
    backend=BaseTokenAuth(),
    on_error=lambda _, exc: PlainTextResponse(str(exc), status_code=401),
)

app.add_middleware(
    PrometheusMiddleware,
    app_name="infrahub",
    group_paths=True,
    prefix="infrahub",
    buckets=[0.1, 0.25, 0.5],
    skip_paths=["/health"],
)
app.add_middleware(InfrahubCORSMiddleware)

app.add_route(path="/metrics", route=handle_metrics)

app.add_route(path="/graphql", route=InfrahubGraphQLApp(playground=True), methods=["GET", "POST", "OPTIONS"])
app.add_route(
    path="/graphql/{branch_name:str}", route=InfrahubGraphQLApp(playground=True), methods=["GET", "POST", "OPTIONS"]
)
app.add_websocket_route(path="/graphql", route=InfrahubGraphQLApp())
app.add_websocket_route(path="/graphql/{branch_name:str}", route=InfrahubGraphQLApp())

if __name__ != "main":
    logger.setLevel(gunicorn_logger.level)
