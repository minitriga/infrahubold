import enum


class PermissionLevel(enum.Flag):
    READ = 1

    WRITE = 2

    ADMIN = 3

    DEFAULT = 0


class DiffAction(enum.Flag):
    ADDED = "added"

    REMOVED = "removed"

    UPDATED = "updated"


class RelationshipStatus(enum.Flag):
    ACTIVE = "active"

    DELETED = "deleted"


# List if Node Labels that are reserved for internal use
INTERNAL_NODE_LABELS = [
    "Attribute",
    "AttributeLocal",
    "AttributeValue",
    "Boolean",
    "Branch",
    "Node",
    "Relationship",
    "Root",
]
