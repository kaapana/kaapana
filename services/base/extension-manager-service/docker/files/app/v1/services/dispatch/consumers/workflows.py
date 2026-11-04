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

    @staticmethod
    def _read_workflow(content: Content) -> dict:
        if not content.path:
            raise ContentError("No path found for content!")
        try:
            with open(content.path / "workflow.json", "r") as f:
                workflow = json.load(f)

            with open(content.path / "workflow_definition.py", "r", encoding="utf-8") as f:
                workflow_definition = f.read()
        except FileNotFoundError as e:
            raise ContentError(f"Required file not found for workflow content: {e.filename}") from e
        except json.JSONDecodeError as e:
            raise ContentError(f"Invalid JSON format in workflow.json: {e.msg}") from e
        except UnicodeDecodeError as e:
            raise ContentError(f"Workflow files must be UTF-8 text: {e}") from e

        if not isinstance(workflow, dict):
            raise ContentError("workflow.json must contain a JSON object.")
        if not isinstance(workflow.get("title"), str) or not workflow["title"].strip():
            raise ContentError("workflow.json must contain a non-empty title.")
        if not workflow_definition.strip():
            raise ContentError("workflow_definition.py is empty.")
        workflow["definition"] = workflow_definition
        return workflow

    def validate(self, content: Content) -> None:
        self._read_workflow(content)

    async def install(self, content: Content) -> InstallationResult:
        workflow = self._read_workflow(content)

        title = workflow["title"]

        # add immutable extension identity labels to workflow
        labels = [
            label
            for label in workflow.get("labels", [])
            if not label.get("key", "").startswith("kaapana.immutable.extension.")
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
