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
    path = MODULE_PATH / "tmp" / timestamp
    os.makedirs(path, exist_ok=True)
    return path


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
