from collections import defaultdict
from itertools import chain
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Self

from infrahub.core.constants import PathResourceType, PathType, SchemaPathType
from infrahub.core.schema import AttributeSchema, GenericSchema, NodeSchema

# DataPath
#   Node
#   Attribute or a Relationship
#   A peer of a node
#   A value or a property
# SchemaPath
# FilePath


class InfrahubPath(BaseModel):
    """A Path represent the location of a single resource stored in Infrahub.
    TODO Add definition of a resource
    """

    def __hash__(self) -> int:
        return hash((type(self),) + tuple(self.__dict__.values()))

    def __str__(self) -> str:
        return self.get_path()

    def get_path(self) -> str:
        raise NotImplementedError()

    # def from_string(self, value: str):
    #     raise NotImplementedError

    # @property
    # def change_type(self) -> str:
    #     if self.path_type in [PathType.ATTRIBUTE, PathType.RELATIONSHIP_MANY, PathType.RELATIONSHIP_ONE]:
    #         if self.property_name and self.property_name != "HAS_VALUE":
    #             return f"{self.path_type.value}_property"
    #         return f"{self.path_type.value}_value"
    #     return self.path_type.value


class DataPath(InfrahubPath):
    resource_type: PathResourceType = Field(PathResourceType.DATA, description="Indicate the type of the resource")
    branch: str = Field(..., description="Name of the branch")
    path_type: PathType
    node_id: str = Field(..., description="Kind of the model in the schema")
    kind: str = Field(..., description="Kind of the main node")
    field_name: Optional[str] = Field(None, description="Name of the field (either an attribute or a relationship)")
    property_name: Optional[str] = Field(None, description="Name of the property")
    peer_id: Optional[str] = Field(None, description="")
    value: Optional[Any] = Field(None, description="Optional value of the resource")

    def get_path(self, with_peer: bool = True) -> str:
        identifier = f"{self.resource_type.value}/{self.node_id}"
        if self.field_name:
            identifier += f"/{self.field_name}"

        if self.path_type == PathType.RELATIONSHIP_ONE and not self.property_name:
            identifier += "/peer"

        if with_peer and self.peer_id:
            identifier += f"/{self.peer_id}"

        if self.property_name and self.property_name == "HAS_VALUE":
            identifier += "/value"
        elif self.property_name:
            identifier += f"/property/{self.property_name}"

        return identifier


class GroupedDataPaths:
    def __init__(self, grouping_attribute: Optional[str] = None, data_paths: Optional[List[DataPath]] = None) -> None:
        self._grouped_data_paths: Dict[Any, List[DataPath]] = defaultdict(list)
        self._grouping_attribute = grouping_attribute
        if data_paths:
            self.add_data_paths(data_paths)

    def add_data_path(self, data_path: DataPath) -> None:
        self.add_data_paths([data_path])

    def add_data_paths(self, data_paths: List[DataPath]) -> None:
        for dp in data_paths:
            if self._grouping_attribute:
                grouping_key = getattr(dp, self._grouping_attribute)
            else:
                grouping_key = None
            self._grouped_data_paths[grouping_key].append(dp)

    def get_data_paths(self, value: Optional[Any] = None) -> List[DataPath]:
        if value:
            return self._grouped_data_paths.get(value, [])
        return list(chain(*self._grouped_data_paths.values()))

    def get_grouping_keys(self) -> List[Any]:
        return list(self._grouped_data_paths.keys())


class SchemaPath(InfrahubPath):
    resource_type: PathResourceType = Field(PathResourceType.SCHEMA, description="Indicate the type of the resource")
    path_type: SchemaPathType
    schema_kind: str = Field(..., description="Kind of the model in the schema")
    schema_id: Optional[str] = Field(None, description="UUID of the model in the schema")
    field_name: Optional[str] = Field(None, description="Name of the field (either an attribute or a relationship)")
    property_name: Optional[str] = Field(None, description="Name of the property")

    def get_path(self) -> str:
        identifier = f"{self.resource_type.value}/{self.schema_kind}"

        if self.field_name:
            identifier += f"/{self.field_name}"

        if self.property_name and not self.path_type == SchemaPathType.NODE:
            identifier += f"/{self.property_name}"

        return identifier

    @classmethod
    def init(
        cls,
        schema: Union[NodeSchema, GenericSchema],
        schema_id: Optional[str] = None,
        field_name: Optional[str] = None,
        property_name: Optional[str] = None,
    ) -> Self:
        if field_name and not schema.get_field(name=field_name, raise_on_error=False):
            raise ValueError(f"Field : {field_name} is not valid for {schema.kind}")

        path_type = SchemaPathType.NODE
        if field_name:
            path_type = (
                SchemaPathType.ATTRIBUTE
                if isinstance(schema.get_field(name=field_name), AttributeSchema)
                else SchemaPathType.RELATIONSHIP
            )

        if field_name and property_name and not hasattr(schema.get_field(name=field_name), property_name):
            raise ValueError(f"Property {property_name} is not valid for {schema.kind}:{field_name}")

        return cls(
            resource_type=PathResourceType.SCHEMA,
            schema_kind=schema.kind,
            path_type=path_type,
            schema_id=schema_id,
            field_name=field_name,
            property_name=property_name,
        )


class FilePath(InfrahubPath):
    resource_type: PathResourceType = Field(PathResourceType.SCHEMA, description="Indicate the type of the resource")
    repository_name: str = Field(..., description="name of the repository")

    def get_path(self) -> str:
        return f"{self.resource_type.value}/{self.repository_name}"