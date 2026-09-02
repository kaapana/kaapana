import pytest
import tempfile
from pathlib import Path
import os
import docker

LOCAL_REGISTRY = "local-only"
MODULE_PATH = Path(__file__).parent
TASK_DIR = Path(MODULE_PATH, "container_templates")


def proxy_buildargs():
    """Forward the CI proxy settings into the image build.

    Docker does not pass the job's environment into build containers, so on a
    proxied runner the Dockerfile's apt-get cannot reach the archives. Both
    casings are emitted: apt reads the lowercase names, most other tools read
    either.
    """
    buildargs = {}
    for name in ("http_proxy", "https_proxy", "no_proxy"):
        value = os.environ.get(name) or os.environ.get(name.upper())
        if value:
            buildargs[name] = value
            buildargs[name.upper()] = value
    return buildargs


@pytest.fixture(scope="session")
def tmp_output_dir():
    yield Path(tempfile.mkdtemp(prefix="task_api_tests_"))


@pytest.fixture(scope="session", autouse=True)
def build_image_locally():
    client = docker.from_env()
    client.images.build(
        path=f"{TASK_DIR}/dummy/",
        tag=f"{LOCAL_REGISTRY}/dummy:latest",
        buildargs=proxy_buildargs(),
    )


@pytest.fixture(autouse=False)
def push_to_registry():
    client = docker.from_env()
    client.login(
        username=os.environ["REGISTRY_USER"],
        password=os.environ["REGISTRY_PASSWORD"],
        registry=os.environ["REGISTRY_URL"],
    )
    client.images.build(
        path=f"{TASK_DIR}/dummy/",
        tag=f"{os.environ["REGISTRY_URL"]}/dummy:latest",
        buildargs=proxy_buildargs(),
    )
    client.images.push(repository=f"{os.environ["REGISTRY_URL"]}/dummy", tag="latest")


def k8s_cluster_available():
    from kubernetes import config, client
    import urllib3

    try:
        config.load_config()
        client.CoreV1Api().list_namespace(_request_timeout=10)
        return True

    except (
        config.config_exception.ConfigException,
        client.ApiException,
        urllib3.exceptions.HTTPError,
    ):
        return False
