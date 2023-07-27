import copy
import enum
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Request
from fastapi.logger import logger
from neo4j import AsyncSession
from pydantic import BaseModel, Field

from infrahub.api.dependencies import get_branch_dep, get_current_user, get_session
from infrahub.core import get_branch, registry
from infrahub.core.branch import Branch, Diff, ObjectConflict, RelationshipDiffElement
from infrahub.core.constants import DiffAction
from infrahub.core.manager import NodeManager
from infrahub.core.schema_manager import INTERNAL_SCHEMA_NODE_KINDS

if TYPE_CHECKING:
    from infrahub.message_bus.rpc import InfrahubRpcClient

# pylint    : disable=too-many-branches

router = APIRouter(prefix="/diff")


class DiffElementType(str, enum.Enum):
    ATTRIBUTE = "Attribute"
    RELATIONSHIP_ONE = "RelationshipOne"
    RELATIONSHIP_MANY = "RelationshipMany"


class DiffSummary(BaseModel):
    added: int = 0
    removed: int = 0
    updated: int = 0

    def inc(self, name: str) -> int:
        """Increase one of the counter by 1.

        Return the new value of the counter.
        """
        try:
            cnt = getattr(self, name)
        except AttributeError as exc:
            raise ValueError(f"{name} is not a valid counter in DiffSummary.") from exc

        new_value = cnt + 1
        setattr(self, name, new_value)

        return new_value


class BranchDiffPropertyValue(BaseModel):
    new: Any
    previous: Any


class BranchDiffProperty(BaseModel):
    branch: str
    type: str
    changed_at: Optional[str]
    action: DiffAction
    value: BranchDiffPropertyValue


class BranchDiffAttribute(BaseModel):
    type: DiffElementType = DiffElementType.ATTRIBUTE
    name: str
    id: str
    changed_at: Optional[str]
    summary: DiffSummary = DiffSummary()
    action: DiffAction
    value: Optional[BranchDiffProperty]
    properties: List[BranchDiffProperty]


class BranchDiffRelationshipPeerNode(BaseModel):
    id: str
    kind: str
    display_label: Optional[str]


class BranchDiffRelationshipOnePeerValue(BaseModel):
    new: Optional[BranchDiffRelationshipPeerNode]
    previous: Optional[BranchDiffRelationshipPeerNode]


class BranchDiffRelationshipOne(BaseModel):
    type: DiffElementType = DiffElementType.RELATIONSHIP_ONE
    branch: str
    id: str
    identifier: str
    summary: DiffSummary = DiffSummary()
    name: str
    peer: BranchDiffRelationshipOnePeerValue
    properties: List[BranchDiffProperty] = Field(default_factory=list)
    changed_at: Optional[str]
    action: DiffAction


class BranchDiffRelationshipManyElement(BaseModel):
    branch: str
    id: str
    identifier: str
    summary: DiffSummary = DiffSummary()
    peer: BranchDiffRelationshipPeerNode
    properties: List[BranchDiffProperty] = Field(default_factory=list)
    changed_at: Optional[str]
    action: DiffAction


class BranchDiffRelationshipMany(BaseModel):
    type: DiffElementType = DiffElementType.RELATIONSHIP_MANY
    branch: str
    identifier: str
    summary: DiffSummary = DiffSummary()
    name: str
    peers: List[BranchDiffRelationshipManyElement] = Field(default_factory=list)

    @property
    def action(self) -> DiffAction:
        if self.summary.added and not self.summary.updated and not self.summary.removed:
            return DiffAction.ADDED
        if not self.summary.added and not self.summary.updated and self.summary.removed:
            return DiffAction.REMOVED
        return DiffAction.UPDATED


class BranchDiffNode(BaseModel):
    branch: str
    kind: str
    id: str
    summary: DiffSummary = DiffSummary()
    display_label: str
    changed_at: Optional[str] = None
    action: DiffAction
    elements: Dict[str, Union[BranchDiffRelationshipOne, BranchDiffRelationshipMany, BranchDiffAttribute]] = Field(
        default_factory=dict
    )


class BranchDiffSummary(BaseModel):
    display_label: str = ""
    action: DiffAction = DiffAction.UNCHANGED
    summary: DiffSummary = DiffSummary()


class BranchDiffEntry(BaseModel):
    kind: str
    id: str
    elements: Dict[str, Union[BranchDiffRelationshipOne, BranchDiffRelationshipMany, BranchDiffAttribute]] = Field(
        default_factory=dict
    )
    source: BranchDiffSummary = BranchDiffSummary()
    target: BranchDiffSummary = BranchDiffSummary()


class BranchDiff(BaseModel):
    diffs: List[BranchDiffNode] = Field(default_factory=list)
    conflicts: Dict[str, ObjectConflict] = Field(default_factory=dict)
    source_branch: str
    target_branch: str
    entries: List[BranchDiffEntry] = Field(default_factory=list)


class BranchDiffFile(BaseModel):
    branch: str
    location: str
    action: DiffAction


class BranchDiffRepository(BaseModel):
    branch: str
    id: str
    display_name: Optional[str] = None
    commit_from: str
    commit_to: str
    files: List[BranchDiffFile] = Field(default_factory=list)


async def get_display_labels_per_kind(kind: str, ids: List[str], branch_name: str, session: AsyncSession):
    """Return the display_labels of a list of nodes of a specific kind."""
    branch = await get_branch(branch=branch_name, session=session)
    schema = registry.get_schema(name=kind, branch=branch)
    fields = schema.generate_fields_for_display_label()
    nodes = await NodeManager.get_many(ids=ids, fields=fields, session=session, branch=branch)
    return {node_id: await node.render_display_label(session=session) for node_id, node in nodes.items()}


async def get_display_labels(
    nodes: Dict[str, Dict[str, List[str]]], session: AsyncSession
) -> Dict[str, Dict[str, str]]:
    """Query the display_labels of a group of nodes organized per branch and per kind."""
    response: Dict[str, Dict[str, str]] = {}
    for branch_name, items in nodes.items():
        if branch_name not in response:
            response[branch_name] = {}
        for kind, ids in items.items():
            labels = await get_display_labels_per_kind(kind=kind, ids=ids, session=session, branch_name=branch_name)
            response[branch_name].update(labels)

    return response


def extract_diff_relationship_one(
    node_id: str, name: str, identifier: str, rels: List[RelationshipDiffElement], display_labels: Dict[str, str]
) -> Optional[BranchDiffRelationshipOne]:
    """Extract a BranchDiffRelationshipOne object from a list of RelationshipDiffElement."""

    changed_at = None

    if len(rels) == 1:
        rel = rels[0]

        if rel.changed_at:
            changed_at = rel.changed_at.to_string()

        peer_list = [rel_node for rel_node in rel.nodes.values() if rel_node.id != node_id]
        if not peer_list:
            logger.warning(
                f"extract_diff_relationship_one: unable to find the peer associated with the node {node_id}, Name: {name}"
            )
            return None

        peer = dict(peer_list[0])
        peer["display_label"] = display_labels.get(peer.get("id", None), "")

        if rel.action.value == "added":
            peer_value = {"new": peer}
        else:
            peer_value = {"previous": peer}

        return BranchDiffRelationshipOne(
            branch=rel.branch,
            id=rel.id,
            name=name,
            identifier=identifier,
            peer=peer_value,
            properties=[prop.to_graphql() for prop in rel.properties.values()],
            changed_at=changed_at,
            action=rel.action,
        )

    if len(rels) == 2:
        actions = [rel.action.value for rel in rels]
        if sorted(actions) != ["added", "removed"]:
            logger.warning(
                f"extract_diff_relationship_one: 2 relationships with actions {actions} received, need to investigate: Node ID {node_id}, Name: {name}"
            )
            return None

        rel_added = [rel for rel in rels if rel.action.value == "added"][0]
        rel_removed = [rel for rel in rels if rel.action.value == "removed"][0]

        peer_added = dict([rel_node for rel_node in rel_added.nodes.values() if rel_node.id != node_id][0])
        peer_added["display_label"] = display_labels.get(peer_added.get("id", None), "")

        peer_removed = dict([rel_node for rel_node in rel_removed.nodes.values() if rel_node.id != node_id][0])
        peer_removed["display_label"] = display_labels.get(peer_removed.get("id", None), "")
        peer_value = {"new": dict(peer_added), "previous": dict(peer_removed)}

        return BranchDiffRelationshipOne(
            branch=rel_added.branch,
            id=rel_added.id,
            name=name,
            identifier=identifier,
            peer=peer_value,
            properties=[prop.to_graphql() for prop in rel_added.properties.values()],
            changed_at=changed_at,
            action="updated",
        )

    if len(rels) > 2:
        logger.warning(
            f"extract_diff_relationship_one: More than 2 relationships received, need to investigate. Node ID {node_id}, Name: {name}"
        )

    return None


def extract_diff_relationship_many(
    node_id: str, name: str, identifier: str, rels: List[RelationshipDiffElement], display_labels: Dict[str, str]
) -> Optional[BranchDiffRelationshipMany]:
    """Extract a BranchDiffRelationshipMany object from a list of RelationshipDiffElement."""

    if not rels:
        return None

    rel_diff = BranchDiffRelationshipMany(
        branch=rels[0].branch,
        name=name,
        identifier=identifier,
    )

    for rel in rels:
        changed_at = None
        if rel.changed_at:
            changed_at = rel.changed_at.to_string()

        peer = [rel_node for rel_node in rel.nodes.values() if rel_node.id != node_id][0].dict(
            exclude={"db_id", "labels"}
        )
        peer["display_label"] = display_labels.get(peer["id"], "")

        rel_diff.summary.inc(rel.action.value)

        rel_diff.peers.append(
            BranchDiffRelationshipManyElement(
                branch=rel.branch,
                id=rel.id,
                identifier=identifier,
                peer=peer,
                properties=[prop.to_graphql() for prop in rel.properties.values()],
                changed_at=changed_at,
                action=rel.action,
            )
        )

    return rel_diff


class DiffPayload:
    def __init__(self, session: AsyncSession, diff: Diff, kinds_to_include: List[str], source_branch: str):
        self.session = session
        self.diff = diff
        self.kinds_to_include = kinds_to_include
        self.conflicts: List[ObjectConflict] = []
        self.diffs: List[BranchDiffNode] = []
        self.source_branch = source_branch
        self.target_branch: str = ""
        self.entries: Dict[str, BranchDiffEntry] = {}
        self.rels_per_node: Dict[str, Dict[str, Dict[str, List[RelationshipDiffElement]]]] = {}
        self.display_labels: Dict[str, Dict[str, str]] = {}
        self.rels: Dict[str, Dict[str, Dict[str, RelationshipDiffElement]]] = {}

    @property
    def impacted_nodes(self) -> List[str]:
        return list(self.entries.keys())

    def _add_node_summary(self, node_id: str, branch: str, action: DiffAction) -> None:
        if branch == self.source_branch:
            self.entries[node_id].source.summary.inc(action.value)
        if branch == self.target_branch:
            self.entries[node_id].target.summary.inc(action.value)

    def _set_display_label(self, node_id: str, branch: str, display_label: str) -> None:
        if not display_label:
            return

        if branch == self.source_branch:
            self.entries[node_id].source.display_label = display_label

        if branch == self.target_branch:
            self.entries[node_id].target.display_label = display_label

        if not self.entries[node_id].source.display_label:
            self.entries[node_id].source.display_label = display_label

        if not self.entries[node_id].target.display_label:
            self.entries[node_id].target.display_label = display_label

    def _set_node_action(self, node_id: str, branch: str, action: DiffAction) -> None:
        if branch == self.source_branch:
            self.entries[node_id].source.action = action

        if branch == self.target_branch:
            self.entries[node_id].target.action = action

    async def _prepare(self) -> None:
        self.rels_per_node = await self.diff.get_relationships_per_node(session=self.session)
        node_ids = await self.diff.get_node_id_per_kind(session=self.session)

        self.display_labels = await get_display_labels(nodes=node_ids, session=self.session)
        self.conflicts = await self.diff.get_conflicts(session=self.session)
        for branch in self.display_labels.keys():
            if branch != self.source_branch:
                self.target_branch = branch

    def _add_node_to_diff(self, node_id: str, kind: str):
        if node_id not in self.entries:
            self.entries[node_id] = BranchDiffEntry(id=node_id, kind=kind)

    async def _process_nodes(self) -> None:
        # Generate the Diff per node and associated the appropriate relationships if they are present in the schema

        nodes = await self.diff.get_nodes(session=self.session)

        for branch_name, items in nodes.items():  # pylint: disable=too-many-nested-blocks
            branch_display_labels = self.display_labels.get(branch_name, {})
            for item in items.values():
                if self.kinds_to_include and item.kind not in self.kinds_to_include:
                    continue

                item_graphql = item.to_graphql()

                # We need to convert the list of attributes to a dict under elements
                item_dict = copy.deepcopy(item_graphql)
                del item_dict["attributes"]
                item_elements = {attr["name"]: attr for attr in item_graphql["attributes"]}

                display_label = branch_display_labels.get(item.id, "")
                node_diff = BranchDiffNode(**item_dict, elements=item_elements, display_label=display_label)
                self._add_node_to_diff(node_id=item_dict["id"], kind=item_dict["kind"])
                self._set_display_label(node_id=item_dict["id"], branch=branch_name, display_label=display_label)
                self._set_node_action(node_id=item_dict["id"], branch=branch_name, action=item_dict["action"])
                schema = registry.get_schema(name=node_diff.kind, branch=node_diff.branch)

                # Extract the value from the list of properties
                for _, element in node_diff.elements.items():
                    node_diff.summary.inc(element.action.value)
                    self._add_node_summary(node_id=item_dict["id"], branch=branch_name, action=element.action)

                    for prop in element.properties:
                        if prop.type == "HAS_VALUE":
                            element.value = prop
                        else:
                            element.summary.inc(prop.action.value)

                    if element.value:
                        element.properties.remove(element.value)

                if item.id in self.rels_per_node[branch_name]:
                    for rel_name, rels in self.rels_per_node[branch_name][item.id].items():
                        if rel_schema := schema.get_relationship_by_identifier(id=rel_name, raise_on_error=False):
                            diff_rel = None
                            if rel_schema.cardinality == "one":
                                diff_rel = extract_diff_relationship_one(
                                    node_id=item.id,
                                    name=rel_schema.name,
                                    identifier=rel_name,
                                    rels=rels,
                                    display_labels=branch_display_labels,
                                )
                            elif rel_schema.cardinality == "many":
                                diff_rel = extract_diff_relationship_many(
                                    node_id=item.id,
                                    name=rel_schema.name,
                                    identifier=rel_name,
                                    rels=rels,
                                    display_labels=branch_display_labels,
                                )

                            if diff_rel:
                                node_diff.elements[diff_rel.name] = diff_rel
                                node_diff.summary.inc(diff_rel.action.value)
                                self._add_node_summary(
                                    node_id=item_dict["id"], branch=branch_name, action=diff_rel.action
                                )

                self.diffs.append(node_diff)

    async def _process_relationships(self) -> None:
        # Check if all nodes associated with a relationship have been accounted for
        # If a node is missing it means its changes are only related to its relationships
        for branch_name, _ in self.rels_per_node.items():
            branch_display_labels = self.display_labels.get(branch_name, {})
            for node_in_rel, _ in self.rels_per_node[branch_name].items():
                if node_in_rel in self.impacted_nodes:
                    continue

                node_diff = None
                for rel_name, rels in self.rels_per_node[branch_name][node_in_rel].items():
                    node_kind = rels[0].nodes[node_in_rel].kind

                    if self.kinds_to_include and node_kind not in self.kinds_to_include:
                        continue

                    schema = registry.get_schema(name=node_kind, branch=branch_name)
                    rel_schema = schema.get_relationship_by_identifier(id=rel_name, raise_on_error=False)
                    if not rel_schema:
                        continue

                    if not node_diff:
                        node_diff = BranchDiffNode(
                            branch=branch_name,
                            id=node_in_rel,
                            kind=node_kind,
                            action=DiffAction.UPDATED,
                            display_label=branch_display_labels.get(node_in_rel, ""),
                        )

                    if rel_schema.cardinality == "one":
                        diff_rel = extract_diff_relationship_one(
                            node_id=node_in_rel,
                            name=rel_schema.name,
                            identifier=rel_name,
                            rels=rels,
                            display_labels=branch_display_labels,
                        )
                        if diff_rel:
                            node_diff.elements[diff_rel.name] = diff_rel
                            node_diff.summary.inc(diff_rel.action.value)

                    elif rel_schema.cardinality == "many":
                        diff_rel = extract_diff_relationship_many(
                            node_id=node_in_rel,
                            name=rel_schema.name,
                            identifier=rel_name,
                            rels=rels,
                            display_labels=branch_display_labels,
                        )
                        if diff_rel:
                            node_diff.elements[diff_rel.name] = diff_rel
                            node_diff.summary.inc(diff_rel.action.value)

                if node_diff:
                    self.diffs.append(node_diff)

    async def generate_diff_payload(self) -> BranchDiff:
        # Query the Diff per Nodes and per Relationships from the database

        self.rels = await self.diff.get_relationships(session=self.session)
        conflict_data = {conflict.path: conflict for conflict in self.conflicts}

        await self._prepare()
        # Organize the Relationships data per node and per relationship name in order to simplify the association with the nodes Later on.

        await self._process_nodes()
        await self._process_relationships()

        return BranchDiff(
            diffs=self.diffs,
            conflicts=conflict_data,
            source_branch=self.source_branch,
            target_branch=self.target_branch,
            entries=list(self.entries.values()),
        )


@router.get("/data")
async def get_diff_data(  # pylint: disable=too-many-branches,too-many-statements
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> BranchDiff:
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    schema = registry.schema.get_full(branch=branch)
    diff_payload = DiffPayload(
        session=session, diff=diff, kinds_to_include=list(schema.keys()), source_branch=branch.name
    )
    return await diff_payload.generate_diff_payload()


@router.get("/schema")
async def get_diff_schema(  # pylint: disable=too-many-branches,too-many-statements
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> BranchDiff:
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    diff_payload = DiffPayload(
        session=session, diff=diff, kinds_to_include=INTERNAL_SCHEMA_NODE_KINDS, source_branch=branch.name
    )
    return await diff_payload.generate_diff_payload()


@router.get("/files")
async def get_diff_files(
    request: Request,
    session: AsyncSession = Depends(get_session),
    branch: Branch = Depends(get_branch_dep),
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    branch_only: bool = True,
    _: str = Depends(get_current_user),
) -> Dict[str, Dict[str, BranchDiffRepository]]:
    response: Dict[str, Dict[str, BranchDiffRepository]] = defaultdict(dict)
    rpc_client: InfrahubRpcClient = request.app.state.rpc_client

    # Query the Diff for all files and repository from the database
    diff = await branch.diff(session=session, diff_from=time_from, diff_to=time_to, branch_only=branch_only)
    diff_files = await diff.get_files(session=session, rpc_client=rpc_client)

    for branch_name, items in diff_files.items():
        for item in items:
            if item.repository not in response[branch_name]:
                response[branch_name][item.repository] = BranchDiffRepository(
                    id=item.repository,
                    display_name=f"Repository ({item.repository})",
                    commit_from=item.commit_from,
                    commit_to=item.commit_to,
                    branch=branch_name,
                )

            response[branch_name][item.repository].files.append(BranchDiffFile(**item.to_graphql()))

    return response
