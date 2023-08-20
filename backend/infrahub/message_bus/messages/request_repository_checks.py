from pydantic import Field

from infrahub.message_bus import InfrahubBaseMessage


class RequestRepositoryChecks(InfrahubBaseMessage):
    """Sent to trigger the checks for a repository to be executed."""

    proposed_change: str = Field(..., description="The unique ID of the Proposed Change")
    repository: str = Field(..., description="The unique ID of the Repository")
    branch: str = Field(..., description="The branch to target")