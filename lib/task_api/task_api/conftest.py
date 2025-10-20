import pytest
import subprocess
from pathlib import Path
import os
from datetime import datetime
import docker

LOCAL_REGISTRY = "local-only"
MODULE_PATH = Path(__file__).parent
TASK_DIR = Path(MODULE_PATH, "container_templates")


@pytest.fixture(scope="session")
def tmp_output_dir():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", MODULE_PATH))
    path = ARTIFACTS_DIR / "tmp" / timestamp
    os.makedirs(path, exist_ok=True)
    yield path


@pytest.fixture(scope="session", autouse=True)
def build_image_locally():
    client = docker.from_env()
    client.images.build(path=f"{TASK_DIR}/dummy/", tag=f"{LOCAL_REGISTRY}/dummy:latest")


@pytest.fixture(autouse=False)
def push_to_registry():
    client = docker.from_env()
    client.login(
        username=os.environ["REGISTRY_USER"],
        password=os.environ["REGISTRY_PASSWORD"],
        registry=os.environ["REGISTRY_URL"],
    )
    client.images.build(
        path=f"{TASK_DIR}/dummy/", tag=f"{os.environ["REGISTRY_URL"]}/dummy:latest"
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
