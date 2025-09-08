import pytest
import subprocess
from pathlib import Path
import os
from datetime import datetime

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
    cmd = [
        "docker",
        "build",
        "-t",
        f"{LOCAL_REGISTRY}/dummy:latest",
        f"{TASK_DIR}/dummy/",
    ]
    subprocess.run(cmd, check=True)

    cmd = [
        "docker",
        "build",
        "-t",
        f"{LOCAL_REGISTRY}/downstream:latest",
        f"{TASK_DIR}/downstream/",
    ]
    subprocess.run(cmd, check=True)


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
