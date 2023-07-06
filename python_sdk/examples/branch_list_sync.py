
from rich import print as rprint

from infrahub_client import InfrahubClientSync


async def main():
    client = InfrahubClientSync.init(address="http://localhost:8000")
    branches = client.branch.all()
    rprint(branches)

if __name__ == "__main__":
    main()
