from infrahub_client import InfrahubClientSync


async def main():
    client = InfrahubClientSync.init(address="http://localhost:8000")
    client.branch.merge(branch_name="new-branch")


if __name__ == "__main__":
    main()