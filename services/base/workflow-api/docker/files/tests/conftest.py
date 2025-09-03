import pytest
import httpx
import requests
import os


def auth_header(host, client_secret):
    # Get access token
    payload = {
        "username": "kaapana",
        "password": "admin",
        "client_id": "kaapana",
        "client_secret": client_secret,
        "grant_type": "password",
    }
    token_url = f"{host}/auth/realms/kaapana/protocol/openid-connect/token"
    token_res = requests.post(token_url, verify=False, data=payload)
    token_res.raise_for_status()
    access_token = token_res.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    return headers


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default=os.getenv("TEST_ENV", "local"),
        help="Test environment: local or k8s",
    )
    parser.addoption(
        "--host",
        action="store",
        default=os.getenv("HOST", "http://localhost:8080"),
        help="Url to the api root",
    )
    parser.addoption(
        "--client-secret",
        action="store",
        default=os.getenv("CLIENT_SECRET", None),
        help="Client secret of the kaapana client in Keycloak",
    )


@pytest.fixture(scope="session")
def client(pytestconfig):
    env = pytestconfig.getoption("env")
    host = pytestconfig.getoption("host")
    if env == "docker-compose":
        return httpx.AsyncClient(base_url=f"{host}/v1", verify=False)
    elif env == "k8s":
        client_secret = pytestconfig.getoption("client_secret")
        headers = auth_header(host, client_secret=client_secret)
        return httpx.AsyncClient(
            base_url=f"{host}/workflow-api/v1", verify=False, headers=headers
        )
