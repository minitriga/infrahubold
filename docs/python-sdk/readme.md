# Python SDK

A Python SDK for Infrahub greatly simplifies how we can interact with Infrahub programmatically.

## Installation

> The Python SDK is currently hosted in the same repository as Infrahub, but once both reaches a better maturity state, the plan is to make it easy to install the SDK as a stand alone package.

For now, the recommendation is to clone the main Infrahub repository on your file system and to install the entire infrahub package in your own repository using a relative path with the `--editable` flag.

```
poetry add --editable <path to the infrahub repository on disk>
```

## Getting Started

The SDK supports both synchronous and asynchronous Python. The default asynchronous version is provided by the `InfrahubClient` class while the synchronous version is using the `InfrahubClientSync` class.


### Dynamic Schema Discovery

By default, the Python client will automatically gather the active schema from Infrahub and all methods will be autogenerated based on that.

+++ Async
```python
from infrahub_client import InfrahubClient

client = await InfrahubClient.init(address="http://localhost:8000")
```
+++ Sync
```python
from infrahub_client import InfrahubClientSync

client = InfrahubClientSync.init(address="http://localhost:8000")
```
+++


### Authentication

The SDK is using a Token based authentication method to authenticate with the API and GraphQL

The token can either be provided with `config=Config(api_token="TOKEN")` at initialization time or it can be automatically retrieved
from the environment variable `INFRAHUB_SDK_API_TOKEN`

> In the demo environment the default token for the Admin account is `06438eb2-8019-4776-878c-0941b1f1d1ec`

+++ Async
```python
from infrahub_client import InfrahubClient, Config

client = await InfrahubClient.init(config=Config(api_token="TOKEN"))
```
+++ Sync
```python
from infrahub_client import InfrahubClientSync, Config

client = InfrahubClientSync.init(config=Config(api_token="TOKEN"))
```
+++
