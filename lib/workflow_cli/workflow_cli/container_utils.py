"""
Utilities for discovering and listing processing containers.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

from .git_utils import GitUtils


class ProcessingContainerInfo(BaseModel):
    """Information about a processing container."""

    name: str
    description: str
    workflow: str
    path: Path
    has_json: bool
    has_dockerfile: bool
    templates: List[str] = []


def find_processing_containers(kaapana_dir: Path) -> List[ProcessingContainerInfo]:
    """
    Discover all processing containers by scanning workflows/*/processing-containers/ folders.

    Looks for processing-container.json and Dockerfile in each container directory.

    Args:
        kaapana_dir: Root directory of Kaapana repository

    Returns:
        List of ProcessingContainerInfo with container details
    """
    workflows_dir = kaapana_dir / "data-processing" / "workflows"
    if not workflows_dir.exists():
        return []

    containers = []

    for workflow_dir in workflows_dir.iterdir():
        if not workflow_dir.is_dir():
            continue

        processing_containers_dir = workflow_dir / "processing-containers"
        if not processing_containers_dir.exists():
            continue

        for container_dir in processing_containers_dir.iterdir():
            if not container_dir.is_dir():
                continue

            json_file = container_dir / "processing-container.json"
            dockerfile = container_dir / "Dockerfile"

            has_json = json_file.exists()
            has_dockerfile = dockerfile.exists()

            # Primary name comes from Dockerfile LABEL IMAGE
            container_name = container_dir.name
            if has_dockerfile:
                try:
                    with open(dockerfile) as f:
                        for line in f:
                            if line.strip().startswith("LABEL IMAGE="):
                                # Extract value from LABEL IMAGE="name" or LABEL IMAGE=name
                                image_name = line.split("=", 1)[1].strip().strip('"')
                                container_name = image_name
                                break
                except (OSError, IndexError):
                    pass

            description = ""
            templates = []

            if has_json:
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                    description = data.get("description", "")
                    templates = [t["identifier"] for t in data.get("templates", [])]
                except (json.JSONDecodeError, KeyError):
                    pass

            containers.append(
                ProcessingContainerInfo(
                    name=container_name,
                    description=description,
                    workflow=workflow_dir.name,
                    path=container_dir,
                    has_json=has_json,
                    has_dockerfile=has_dockerfile,
                    templates=templates,
                )
            )

    return sorted(containers, key=lambda c: c.name.lower())


def get_container_by_name(kaapana_dir: Path, name: str) -> Optional[ProcessingContainerInfo]:
    """
    Find a specific container by name.

    Args:
        kaapana_dir: Root directory of Kaapana repository
        name: Container name to search for

    Returns:
        ProcessingContainerInfo if found, None otherwise
    """
    containers = find_processing_containers(kaapana_dir)
    name_lower = name.lower()

    for container in containers:
        if container.name.lower() == name_lower or container.path.name == name_lower:
            return container

    return None


def build_and_push_processing_containers(
    kaapana_dir: Path,
    build: bool = True,
    push: bool = False,
    registry_url: Optional[str] = None,
    docker_cmd: str = "docker",
    registry_username: Optional[str] = None,
    registry_password: Optional[str] = None,
    workflow: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Build (and optionally push) all processing containers found in workflows.

    Args:
        kaapana_dir: Root path of the kaapana repo
        build: Whether to run `docker build` for each container
        push: Whether to `docker push` created tags
        registry_prefix: Optional registry prefix to prepend to image name
        docker_cmd: Docker CLI command (defaults to `docker`)

    Returns:
        List of result dicts with keys: `container`, `image`, `status`, `message`.
    """
    containers = find_processing_containers(kaapana_dir)
    if workflow:
        containers = [c for c in containers if c.workflow == workflow]
    version, _, _, _ = GitUtils.get_repo_info(str(kaapana_dir))

    results = []

    # If pushing and credentials provided, try to login once to the registry host
    if push and registry_username and registry_password and registry_url:
        registry_host = str(registry_url).split("/")[0]
        try:
            login_cmd = [
                docker_cmd,
                "login",
                registry_host,
                "-u",
                registry_username,
                "-p",
                registry_password,
            ]
            subprocess.run(login_cmd, check=True)
        except subprocess.CalledProcessError as e:
            # Abort early - login failed
            return [
                {"container": "<login>", "status": "error", "message": f"docker login failed: {e}"}
            ]

    for c in containers:
        if not c.has_dockerfile:
            results.append(
                {"container": c.path.name, "status": "skipped", "message": "no Dockerfile"}
            )
            continue

        image_name = c.name.split("/")[-1]
        tag = f"{registry_url}/{image_name}:{version}"

        try:
            if build:
                build_cmd = [docker_cmd, "build", "-t", tag, str(c.path)]
                subprocess.run(build_cmd, check=True)

            if push:
                push_cmd = [docker_cmd, "push", tag]
                subprocess.run(push_cmd, check=True)

            results.append(
                {
                    "container": c.path.name,
                    "image": image_name,
                    "status": "ok",
                    "message": "built/pushed",
                }
            )
        except subprocess.CalledProcessError as e:
            results.append(
                {
                    "container": c.path.name,
                    "image": image_name,
                    "status": "error",
                    "message": str(e),
                }
            )

    return results
