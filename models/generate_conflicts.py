import logging
import uuid
from collections import defaultdict
from ipaddress import IPv4Network
from typing import Dict, List

from infrahub_sdk import UUIDT, InfrahubClient, InfrahubNode, NodeStore

# flake8: noqa
# pylint: skip-file

DEVICE_ROLES = ["edge"]
INTF_ROLES = ["backbone", "transit", "peering", "peer", "loopback", "management", "spare"]
VLAN_ROLES = ["server"]

SITES = ["atl", "ord", "jfk", "den", "dfw", "iad", "bkk", "sfo", "iah", "mco"]

PLATFORMS = (
    ("Cisco IOS", "ios", "ios", "cisco_ios", "ios"),
    ("Cisco NXOS SSH", "nxos_ssh", "nxos_ssh", "cisco_nxos", "nxos"),
    ("Juniper JunOS", "junos", "junos", "juniper_junos", "junos"),
    ("Arista EOS", "eos", "eos", "arista_eos", "eos"),
)

DEVICES = (
    ("edge1", "active", "7280R3", "profile1", "edge", ["red", "green"], "Arista EOS"),
    ("edge2", "active", "ASR1002-HX", "profile1", "edge", ["red", "blue", "green"], "Cisco IOS"),
)


NETWORKS_POOL_INTERNAL = IPv4Network("10.0.0.0/8").subnets(new_prefix=16)
LOOPBACK_POOL = next(NETWORKS_POOL_INTERNAL).hosts()
P2P_NETWORK_POOL = next(NETWORKS_POOL_INTERNAL).subnets(new_prefix=31)
NETWORKS_POOL_EXTERNAL = IPv4Network("203.0.113.0/24").subnets(new_prefix=29)

MANAGEMENT_IPS = IPv4Network("172.20.20.16/28").hosts()


GROUPS = (
    ("edge_router", "Edge Router"),
    ("cisco_devices", "Cisco Devices"),
    ("arista_devices", "Arista Devices"),
    ("transit_interfaces", "Transit Interface"),
)


store = NodeStore()


async def group_add_member(client: InfrahubClient, group: InfrahubNode, members: List[InfrahubNode], branch: str):
    members_str = ["{ id: " + f'"{member.id}"' + " }" for member in members]
    query = """
    mutation {
        RelationshipAdd(
            data: {
                id: "%s",
                name: "members",
                nodes: [ %s ]
            }
        ) {
            ok
        }
    }
    """ % (
        group.id,
        ", ".join(members_str),
    )

    await client.execute_graphql(query=query, branch_name=branch)

ORGANIZATIONS = (
    ["Telia", 1299],
    ["Colt", 8220],
    ["Verizon", 701],
    ["GTT", 3257],
    ["Hurricane Electric", 6939],
    ["Lumen", 3356],
    ["Zayo", 6461],
    ["Duff", 64496],
    ["Equinix", 24115],
)

# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(client: InfrahubClient, log: logging.Logger, branch: str):

    # ------------------------------------------
    # Create User Accounts, Groups & Organizations & Platforms
    # ------------------------------------------
    batch = await client.create_batch()


    # for group in GROUPS:
    #     obj = await client.create(branch=branch, kind="CoreStandardGroup", data={"name": group[0], "label": group[1]})

    #     batch.add(task=obj.save, node=obj)
    #     store.set(key=group[0], node=obj)

    # for account in ACCOUNTS:
    #     obj = await client.create(
    #         branch=branch,
    #         kind="CoreAccount",
    #         data={"name": account[0], "password": account[2], "type": account[1], "role": account[3]},
    #     )
    #     batch.add(task=obj.save, node=obj)
    #     store.set(key=account[0], node=obj)

    for org in ORGANIZATIONS:

        randstr = str(uuid.uuid4())[:8]
        obj = await client.create(
            branch=branch, kind="CoreOrganization", data={"name": {"value": f"{org[0]}-{randstr}", "is_protected": True}}
        )
        batch.add(task=obj.save, node=obj)
        store.set(key=org[0], node=obj)

    # Create all Groups, Accounts and Organizations
    async for node, _ in batch.execute():
        log.info(f"{node._schema.kind} Created {node.name.value}")
