from infrahub.core.initialization import create_branch


async def test_schema_endpoint_default_branch(session, client, client_headers, default_branch, car_person_data):
    # Must execute in a with block to execute the startup/shutdown events
    with client:
        response = client.get(
            "/schema",
            headers=client_headers,
        )

    assert response.status_code == 200
    assert response.json() is not None

    schema = response.json()

    assert "nodes" in schema
    assert len(schema["nodes"]) == 21


async def test_schema_endpoint_branch1(session, client, client_headers, default_branch, car_person_data):
    await create_branch(branch_name="branch1", session=session)

    # Must execute in a with block to execute the startup/shutdown events
    with client:
        response = client.get(
            "/schema?branch=branch1",
            headers=client_headers,
        )

    assert response.status_code == 200
    assert response.json() is not None

    schema = response.json()

    assert "nodes" in schema
    assert len(schema["nodes"]) == 21


async def test_schema_endpoint_wrong_branch(session, client, client_headers, default_branch, car_person_data):
    # Must execute in a with block to execute the startup/shutdown events
    with client:
        response = client.get(
            "/schema?branch=notvalid",
            headers=client_headers,
        )

    assert response.status_code == 400
    assert response.json() is not None
