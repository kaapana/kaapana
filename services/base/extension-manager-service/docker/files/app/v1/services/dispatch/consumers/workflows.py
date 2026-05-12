from ..content import (
    Content,
    ContentInstaller,
    InstallationResult,
)

from ..exceptions import ConsumerError, ContentError


import json
import asyncio
import httpx
from pathlib import Path

from kaapanapy.logger import get_logger

logger = get_logger(__name__)


class WorkflowInstaller(ContentInstaller):
    workflow_api_url = "http://workflow-api.services.svc:80/v1"

    def can_install(self, content: Content) -> bool:
        return content.content_type == "workflow-v1"

    async def install(self, content: Content) -> InstallationResult:
        installation_success = False
        try:
            with open(content.path / "workflow.json", "r") as f:
                workflow = json.load(f)

            with open(
                content.path / "workflow_definition.py", "r", encoding="utf-8"
            ) as f:
                workflow_definition = f.read()
                workflow["definition"] = workflow_definition
        except FileNotFoundError as e:
            raise ContentError(
                f"Required file not found for workflow content: {e.filename}"
            ) from e
        except json.JSONDecodeError as e:
            raise ContentError(f"Invalid JSON format in workflow.json: {e.msg}") from e

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WorkflowInstaller.workflow_api_url}/workflows",
                json=workflow,
            )
        try:
            response.raise_for_status()
            installation_success = True
        except httpx.HTTPStatusError as e:
            raise ConsumerError(
                f"Failed to install workflow, API responded with status code {response.status_code}: {response.text}"
            ) from e

        return InstallationResult(
            success=installation_success,
            message=f"Workflow installed with status code {response.status_code}",
            location=response.headers.get("Location"),
        )

    async def uninstall(self, location: str) -> None:
        logger.info(f"Uninstalling workflow at {location}")
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{WorkflowInstaller.workflow_api_url}{location}",
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ConsumerError(
                f"Failed to uninstall workflow, API responded with status code {response.status_code}: {response.text}"
            ) from e
