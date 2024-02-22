from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from graphene import Field, Int, List, ObjectType, String
from infrahub_sdk.utils import extract_fields_first_node

from infrahub.core.query.relationship import RelationshipGetByIdentifierQuery
from infrahub.graphql.types import RelationshipNode

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo

    from infrahub.graphql import GraphqlContext


class Relationships(ObjectType):
    edges = List(RelationshipNode)
    count = Int()

    @staticmethod
    async def resolve(
        root: dict,  # pylint: disable=unused-argument
        info: GraphQLResolveInfo,
        limit: int = 10,
        offset: int = 0,
        ids: Optional[list] = None,
    ) -> Dict[str, Any]:
        context: GraphqlContext = info.context
        ids = ids or []

        fields = await extract_fields_first_node(info)

        response = {}

        query = await RelationshipGetByIdentifierQuery.init(
            db=context.db, branch=context.branch, at=context.at, identifiers=ids, limit=limit, offset=offset
        )

        if "count" in fields:
            response["count"] = await query.count(db=context.db)

        if "edges" in fields:
            response["edges"] = []
            # await query.execute(db=context.db)
            # query.get_results()

        return response


Relationship = Field(
    Relationships,
    resolver=Relationships.resolve,
    limit=Int(required=False),
    offset=Int(required=False),
    ids=List(String),
)
