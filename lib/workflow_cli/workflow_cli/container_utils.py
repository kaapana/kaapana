"""
Utilities for discovering and listing processing containers.
"""

import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


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


def get_container_by_name(
    kaapana_dir: Path, name: str
) -> Optional[ProcessingContainerInfo]:
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
