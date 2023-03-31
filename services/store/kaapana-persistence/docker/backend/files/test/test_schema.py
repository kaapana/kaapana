import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_read_schema_without_version(client: AsyncClient):
    response = await client.get("/schema/")
    # response = client.get("/schema/")
    assert response.status_code == 200
    assert response.json() == [
        "urn:kaapana:Dataset",
        "urn:kaapana:Experiment",
        "urn:kaapana:Instance",
        "urn:kaapana:Job",
    ]


@pytest.mark.anyio
async def test_read_schema_with_version(client: AsyncClient):
    response = await client.get("/schema/")
    # response = client.get("/schema/?include_version=true")
    assert response.status_code == 200
    assert response.json() == [
        "urn:kaapana:Dataset",
        "urn:kaapana:Experiment",
        "urn:kaapana:Instance",
        "urn:kaapana:Job",
    ]
