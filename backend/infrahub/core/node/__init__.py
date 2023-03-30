from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, TypeVar, Union
from uuid import UUID

from infrahub.core import get_branch, registry
from infrahub.core.query.node import NodeCreateQuery, NodeDeleteQuery, NodeGetListQuery
from infrahub.core.schema import (
    ATTRIBUTES_MAPPING,
    AttributeSchema,
    NodeSchema,
    RelationshipSchema,
)
from infrahub.exceptions import ValidationError
from infrahub_client.timestamp import Timestamp
from infrahub.utils import intersection
from ..attribute import BaseAttribute
from ..relationship import RelationshipManager
from ..utils import update_relationships_to
from .base import BaseNode, BaseNodeMeta, BaseNodeOptions

if TYPE_CHECKING:
    from neo4j import AsyncSession

    from infrahub.core.branch import Branch

# ---------------------------------------------------------------------------------------
# Type of Nodes
#  - Core node, wo/ branch : Branch, MergeRequest, Comment
#  - Core node, w/ branch : Repository, RFile, GQLQuery, Permission, Account, Groups, Schema
#  - Location Node : Location,
#  - Select Node : Status, Role, Manufacturer etc ..
#  -
# ---------------------------------------------------------------------------------------

# pylint: disable=redefined-builtin,too-many-branches


SelfNode = TypeVar("SelfNode", bound="Node")


class Node(BaseNode, metaclass=BaseNodeMeta):
    @classmethod
    def __init_subclass_with_meta__(  # pylint: disable=arguments-differ
        cls,
        _meta=None,
        default_filter=None,
        **options,
    ):
        if not _meta:
            _meta = BaseNodeOptions(cls)

        _meta.default_filter = default_filter
        super(Node, cls).__init_subclass_with_meta__(_meta=_meta, **options)

    def get_kind(self):
        return self._schema.kind

    def __repr__(self):
        return f"{self.get_kind()}(ID: {str(self.id)})"

    def __init__(
        self,
        schema: NodeSchema,
        branch: Branch,
        at: Timestamp,
    ):
        self._schema: NodeSchema = schema
        self._branch: Branch = branch
        self._at: Timestamp = at

        self._updated_at: Optional[Timestamp] = None
        self.id: str = None
        self.db_id: str = None

        self._source: Node = None
        self._owner: Node = None
        self._is_protected: bool = None

        # Lists of attributes and relationships names
        self._attributes: List[str] = []
        self._relationships: List[str] = []

    @classmethod
    async def init(
        cls,
        session: AsyncSession,
        schema: Union[NodeSchema, str],
        branch: Optional[Union[Branch, str]] = None,
        at: Optional[Union[Timestamp, str]] = None,
    ) -> Node:
        attrs = {}

        branch = await get_branch(branch=branch, session=session)

        if isinstance(schema, NodeSchema):
            attrs["schema"] = schema
        elif isinstance(schema, str):
            # TODO need to raise a proper exception for this, right now it will raise a generic ValueError
            attrs["schema"] = registry.get_schema(name=schema, branch=branch)
        else:
            raise ValueError(f"Invalid schema provided {schema}")

        if not attrs["schema"].branch:
            attrs["branch"] = None
        else:
            attrs["branch"] = branch

        attrs["at"] = Timestamp(at)

        return cls(**attrs)

    async def _process_fields(self, fields: dict, profile: Optional[Node], session: AsyncSession):
        errors = []

        if "_source" in fields.keys():
            self._source = fields["_source"]
        if "_owner" in fields.keys():
            self._owner = fields["_owner"]

        # -------------------------------------------
        # Validate Input
        # -------------------------------------------
        for field_name in fields.keys():
            if field_name not in self._schema.valid_input_names:
                errors.append(ValidationError({field_name: f"{field_name} is not a valid input for {self.get_kind()}"}))


        # -------------------------------------------
        # Extend attributes with value from Profile
        # -------------------------------------------
        if profile:
            shared_attribute_names = intersection(profile._schema.attribute_names, self._schema.attribute_names)
            # For now we assume that nothing has been provided for the attribute but later we'll need to consider the metadata as well
            for attr_name in shared_attribute_names:
                if attr_name in fields:
                    continue

                fields[attr_name] = {
                    "is_inherited": True,
                    "value": getattr(profile, attr_name).value,
                    "source": profile.id,
                }

        # If the object is new, we need to ensure that all mandatory attributes and relationships have been provided
        # NOTE we'll need to account for profile(s) at this point
        if not self.id:
            for mandatory_attr in self._schema.mandatory_attribute_names:
                if mandatory_attr not in fields.keys():
                    errors.append(
                        ValidationError({mandatory_attr: f"{mandatory_attr} is mandatory for {self.get_kind()}"})
                    )

            for mandatory_rel in self._schema.mandatory_relationship_names:
                if mandatory_rel not in fields.keys():
                    errors.append(
                        ValidationError({mandatory_rel: f"{mandatory_rel} is mandatory for {self.get_kind()}"})
                    )

        if errors:
            raise ValidationError(errors)

        # -------------------------------------------
        # Generate Attribute and Relationship and assign them
        # -------------------------------------------
        for attr_schema in self._schema.attributes:
            self._attributes.append(attr_schema.name)

            # Check if there is a more specific generator present
            # Otherwise use the default generator
            generator_method_name = "_generate_attribute_default"
            if hasattr(self, f"generate_{attr_schema.name}"):
                generator_method_name = f"generate_{attr_schema.name}"

            generator_method = getattr(self, generator_method_name)
            try:
                setattr(
                    self,
                    attr_schema.name,
                    await generator_method(
                        session=session,
                        name=attr_schema.name,
                        schema=attr_schema,
                        data=fields.get(attr_schema.name, None),
                    ),
                )
            except ValidationError as exc:
                errors.append(exc)

        for rel_schema in self._schema.relationships:
            self._relationships.append(rel_schema.name)

            # Check if there is a more specific generator present
            # Otherwise use the default generator
            generator_method_name = "_generate_relationship_default"
            if hasattr(self, f"generate_{rel_schema.name}"):
                generator_method_name = f"generate_{rel_schema.name}"

            generator_method = getattr(self, generator_method_name)
            try:
                setattr(
                    self,
                    rel_schema.name,
                    await generator_method(
                        session=session, name=rel_schema.name, schema=rel_schema, data=fields.get(rel_schema.name, None)
                    ),
                )
            except ValidationError as exc:
                errors.append(exc)

        if errors:
            raise ValidationError(errors)

        # Check if any post processor have been defined
        # A processor can be used for example to assigne a default value
        for name in self._attributes + self._relationships:
            if hasattr(self, f"process_{name}"):
                await getattr(self, f"process_{name}")(session=session)

    async def _generate_relationship_default(
        self, session: AsyncSession, name: str, schema: RelationshipSchema, data: Any  # pylint: disable=unused-argument
    ) -> RelationshipManager:
        rm = await RelationshipManager.init(
            session=session,
            data=data,
            schema=schema,
            branch=self._branch,
            at=self._at,
            node=self,
        )

        return rm

    async def _generate_attribute_default(
        self, session: AsyncSession, name: str, schema: AttributeSchema, data: Any  # pylint: disable=unused-argument
    ) -> BaseAttribute:
        attr_class = ATTRIBUTES_MAPPING[schema.kind]
        attr = attr_class(
            data=data,
            name=name,
            schema=schema,
            branch=self._branch,
            at=self._at,
            node=self,
            source=self._source,
            owner=self._owner,
        )
        return attr

    async def process_label(self, session: AsyncSession):  # pylint: disable=unused-argument
        # If there label and name are both defined for this node
        #  if label is not define, we'll automatically populate it with a human friendy vesion of name
        # pylint: disable=no-member
        if not self.id and hasattr(self, "label") and hasattr(self, "name"):
            if self.label.value is None and self.name.value:
                self.label.value = " ".join([word.title() for word in self.name.value.split("_")])

    async def new(self, session: AsyncSession, **kwargs) -> SelfNode:
        await self._process_fields(session=session, fields=kwargs)
        return self

    async def load(
        self,
        session: AsyncSession,
        id: UUID = None,
        db_id: Optional[int] = None,
        updated_at: Union[Timestamp, str] = None,
        **kwargs,
    ) -> SelfNode:
        self.id = id
        self.db_id = db_id

        if updated_at:
            self._updated_at = Timestamp(updated_at)

        await self._process_fields(session=session, fields=kwargs)
        return self

    async def _create(self, session: AsyncSession, at: Optional[Timestamp] = None):
        create_at = Timestamp(at)

        query = await NodeCreateQuery.init(session=session, node=self, at=create_at)
        await query.execute(session=session)
        self.id, self.db_id = query.get_new_ids()
        self._at = create_at
        self._updated_at = create_at

        # Go over the list of Attribute and create them one by one
        for name in self._attributes:
            attr: BaseAttribute = getattr(self, name)
            # Handle LocalAttribute attributes
            if issubclass(attr.__class__, BaseAttribute):
                await attr.save(at=create_at, session=session)

        # Go over the list of relationships and create them one by one
        for name in self._relationships:
            rel: RelationshipManager = getattr(self, name)
            await rel.save(at=create_at, session=session)

        return True

    async def _update(
        self,
        session: AsyncSession,
        at: Optional[Timestamp] = None,
    ):
        """Update the node in the database if needed."""

        update_at = Timestamp(at)

        # Go over the list of Attribute and update them one by one
        for name in self._attributes:
            attr: BaseAttribute = getattr(self, name)
            await attr.save(at=update_at, session=session)

        # Go over the list of relationships and update them one by one
        for name in self._relationships:
            rel: RelationshipManager = getattr(self, name)
            await rel.save(at=update_at, session=session)

    async def save(
        self,
        session: AsyncSession,
        at: Optional[Timestamp] = None,
    ) -> SelfNode:
        """Create or Update the Node in the database."""

        save_at = Timestamp(at)

        if self.id:
            await self._update(at=save_at, session=session)
            return self

        await self._create(at=save_at, session=session)
        return self

    async def delete(self, session: AsyncSession, at: Optional[Timestamp] = None):
        """Delete the Node in the database."""

        delete_at = Timestamp(at)

        # Ensure the node can be safely deleted first TODO
        #  - Check if there is a relationship pointing to it that is mandatory
        #  - Check if some nodes must be deleted too CASCADE (TODO)

        # Go over the list of Attribute and update them one by one
        for name in self._attributes:
            attr: BaseAttribute = getattr(self, name)
            await attr.delete(at=delete_at, session=session)

        # Go over the list of relationships and update them one by one
        for name in self._relationships:
            rel: RelationshipManager = getattr(self, name)
            await rel.delete(at=delete_at, session=session)

        # Need to check if there are some unidirectional relationship as well
        # For example, if we delete a tag, we must check the permissions and update all the relationships pointing at it

        # Update the relationship to the branch itself
        query = await NodeGetListQuery.init(
            session=session, schema=self._schema, filters={"id": self.id}, branch=self._branch, at=delete_at
        )
        await query.execute(session=session)
        result = query.get_result()

        if result.get("br").get("name") == self._branch.name:
            await update_relationships_to([result.get("rb").element_id], to=delete_at, session=session)

        query = await NodeDeleteQuery.init(session=session, node=self, at=delete_at)
        await query.execute(session=session)

    async def to_graphql(self, session: AsyncSession, fields: dict = None) -> dict:
        """Generate GraphQL Payload for all attributes

        Returns:
            (dict): Return GraphQL Payload
        """

        response = {"id": self.id, "type": self.get_kind()}

        for field_name in fields.keys():
            if field_name in ["id"] or field_name in self._schema.relationship_names:
                continue

            if field_name == "__typename":
                response[field_name] = self.get_kind()
                continue

            if field_name == "display_label":
                response[field_name] = await self.render_display_label(session=session)
                continue

            if field_name == "_updated_at":
                if self._updated_at:
                    response[field_name] = await self._updated_at.to_graphql()
                else:
                    response[field_name] = None
                continue

            field = getattr(self, field_name, None)

            if not field:
                response[field_name] = None
                continue

            response[field_name] = await field.to_graphql(session=session, fields=fields[field_name])

        return response

    async def from_graphql(self, session: AsyncSession, data: dict) -> bool:
        """Update object from a GraphQL payload."""

        changed = False

        STANDARD_FIELDS = ["value", "is_protected", "is_visible"]
        NODE_FIELDS = ["source", "owner"]

        for key, value in data.items():
            if key in self._attributes and isinstance(value, dict):
                for field_name in value.keys():
                    if field_name in STANDARD_FIELDS:
                        attr = getattr(self, key)
                        if getattr(attr, field_name) != value.get(field_name):
                            setattr(attr, field_name, value.get(field_name))
                            changed = True

                    elif field_name in NODE_FIELDS:
                        attr = getattr(self, key)
                        # Right now we assume that the UUID is provided from GraphQL
                        # so we compare the value with <node>_id
                        if getattr(attr, f"{field_name}_id") != value.get(field_name):
                            setattr(attr, field_name, value.get(field_name))
                            changed = True

            if key in self._relationships:
                rel: RelationshipManager = getattr(self, key)
                changed |= await rel.update(session=session, data=value)

        return changed

    async def render_display_label(self, session: AsyncSession):  # pylint: disable=unused-argument
        if not self._schema.display_labels:
            return repr(self)

        display_elements = []
        for item in self._schema.display_labels:
            item_elements = item.split("__")
            if len(item_elements) != 2:
                raise ValidationError("Display Label can only have one level")

            if item_elements[0] not in self._schema.attribute_names:
                raise ValidationError("Only Attribute can be used in Display Label")

            attr = getattr(self, item_elements[0])
            display_elements.append(str(getattr(attr, item_elements[1])))

        return " ".join(display_elements)
