import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.anyio
async def test_read_healt(client: AsyncClient):
    response = await client.get("/health/")
    assert response.status_code == 200
