import json
import os
import pytest
import requests
from pathlib import Path

from kaapana_containers.registries.registry import OCIError
from kaapana_extensions.extensions import ExtensionUtilityLibrary

# Repo unique per xdist worker: when KAAPANA_TEST_REGISTRY points all workers
# at one shared registry, clean_registry must not wipe another worker's tags
# (the client — and thus the wipe — is repo-scoped).
_REPO = f"test/extensions-{os.environ.get('PYTEST_XDIST_WORKER', 'main')}"
_USER = "user"
_PASSWORD = "pass"


def _registry_responsive(url: str) -> bool:
    try:
        return requests.get(f"{url}/v2/", timeout=2).status_code == 200
    except requests.exceptions.ConnectionError:
        return False


@pytest.fixture(scope="session")
def docker_compose_file():
    return str(Path(__file__).parent / "docker-compose.yml")


@pytest.fixture(scope="session")
def registry_url(request):
    # Set KAAPANA_TEST_REGISTRY=http://localhost:5001 to skip Docker and use
    # a registry you started manually (or the CI service container) — the
    # docker fixtures are requested lazily so no docker daemon is needed then.
    external = os.environ.get("KAAPANA_TEST_REGISTRY", "").strip()
    if external:
        if not _registry_responsive(external):
            pytest.fail(f"KAAPANA_TEST_REGISTRY={external!r} is not reachable")
        return external

    docker_ip = request.getfixturevalue("docker_ip")
    docker_services = request.getfixturevalue("docker_services")
    port = docker_services.port_for("registry", 5000)
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(
        check=lambda: _registry_responsive(url),
        timeout=30.0,
        pause=0.5,
    )
    return url


@pytest.fixture(autouse=True)
async def clean_registry(client):
    """Wipe all tags before each test so tests start with a clean registry."""
    try:
        for tag in await client.list_tags():
            await client.delete_tag(tag)
    except OCIError:
        pass
    yield


@pytest.fixture
async def client(registry_url):
    async with ExtensionUtilityLibrary(
        registry=registry_url,
        repo=_REPO,
        username=_USER,
        password=_PASSWORD,
    ) as lib:
        yield lib


@pytest.fixture
def registry_opts(registry_url):
    return [
        "--registry",
        registry_url,
        "--repo",
        _REPO,
        "--user",
        _USER,
        "--password",
        _PASSWORD,
    ]


@pytest.fixture
def ext_dir(tmp_path):
    ext = tmp_path / "my-ext"
    ext.mkdir()
    charts = ext / "charts"
    charts.mkdir()
    (charts / "Chart.yaml").write_text("apiVersion: v2\nname: my-ext\n")
    manifest = {
        "name": "my-ext",
        "id": "aaaaaaaa-0000-0000-0000-000000000001",
        "version": "1.0.0",
        "contents": [
            {
                "name": "charts",
                "contentType": "helm",
                "files": [{"path": "Chart.yaml"}],
            }
        ],
    }
    (ext / "extension_manifest.json").write_text(json.dumps(manifest, indent=2))
    return ext


@pytest.fixture
def ext_archive(ext_dir, tmp_path):
    archives = list(
        ExtensionUtilityLibrary.build(str(ext_dir), output=tmp_path / "build")
    )
    assert len(archives) == 1
    return archives[0][1]
