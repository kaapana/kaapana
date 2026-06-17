import json

import httpx
from v1.services.logger import get_logger

from ..content import (
    Content,
    ContentInstaller,
    InstallationResult,
)
from ..exceptions import ConsumerError, ContentError

logger = get_logger(__name__)


class WorkflowInstaller(ContentInstaller):
    workflow_api_url = "http://workflow-api.services.svc:80/v1"

    def can_install(self, content: Content) -> bool:
        return content.content_type == "workflow-v1"

    async def install(self, content: Content) -> InstallationResult:
        if not content.path:
            raise ContentError("No path found for content!")
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

        title = workflow.get("title", "<unknown>")

        # add immutable extension identity labels to workflow
        labels = [
            l
            for l in workflow.get("labels", [])
            if not l.get("key", "").startswith("kaapana.immutable.extension.")
        ]
        if content.extension_id is not None:
            labels.extend(
                [
                    {
                        "key": "kaapana.immutable.extension.id",
                        "value": str(content.extension_id),
                    },
                    {
                        "key": "kaapana.immutable.extension.name",
                        "value": content.extension_name,
                    },
                    {
                        "key": "kaapana.immutable.extension.version",
                        "value": content.extension_version,
                    },
                    {
                        "key": "kaapana.immutable.extension.workflow_name",
                        "value": content.name,
                    },
                ]
            )
        workflow["labels"] = labels

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WorkflowInstaller.workflow_api_url}/workflows",
                json=workflow,
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ConsumerError(
                f"Failed to install workflow '{title}', API responded with "
                f"status code {response.status_code}: {response.text}"
            ) from e

        return InstallationResult(
            success=True,
            message=f"Workflow '{title}' created",
            location=response.headers.get("Location"),
        )

    async def uninstall(self, content: Content) -> None:
        logger.info(f"Uninstalling workflow at {content.location}")
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{WorkflowInstaller.workflow_api_url}{content.location}",
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ConsumerError(
                f"Failed to uninstall workflow, API responded with status code {response.status_code}: {response.text}"
            ) from e
