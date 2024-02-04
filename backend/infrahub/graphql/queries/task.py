from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from graphene import Field, Int, List, ObjectType, String
from infrahub_sdk.utils import extract_fields_first_node

from infrahub.core.task import Task as TaskNode
from infrahub.graphql.types import TaskNodes

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo

    from infrahub.database import InfrahubDatabase


class Tasks(ObjectType):
    edges = Field(TaskNodes)
    count = Int()

    @staticmethod
    async def resolve(
        root: dict,  # pylint: disable=unused-argument
        info: GraphQLResolveInfo,
        limit: int = 10,
        offset: int = 0,
        related_node__ids: Optional[list] = None,
    ) -> Dict[str, Any]:
        related_nodes = related_node__ids or []
        return await Tasks.query(info=info, limit=limit, offset=offset, related_nodes=related_nodes)

    @classmethod
    async def query(
        cls,
        info: GraphQLResolveInfo,
        limit: int,
        offset: int,
        related_nodes: list[str],
    ) -> Dict[str, Any]:
        db: InfrahubDatabase = info.context.get("infrahub_database")
        fields = await extract_fields_first_node(info)

        return await TaskNode.query(db=db, fields=fields, limit=limit, offset=offset, related_nodes=related_nodes)


Task = Field(
    Tasks,
    resolver=Tasks.resolve,
    limit=Int(required=False),
    offset=Int(required=False),
    related_node__ids=List(String),
)