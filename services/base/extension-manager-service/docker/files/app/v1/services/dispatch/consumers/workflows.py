from ..content import (
    Content,
    ContentInstaller,
    InstallationResult,
    ContentDiscovery,
)

import json
import asyncio
import httpx
from pathlib import Path


class WorkflowContent(Content):
    @property
    def content_type(self) -> str:
        return "workflow"


class WorkflowDiscovery(ContentDiscovery):
    def matches(self, path: Path) -> bool:
        return (path / "workflow.json").exists() and (
            path / "workflow_definition.py"
        ).exists()

    def create(self, path: Path) -> Content:
        return WorkflowContent(path=path)


class WorkflowInstaller(ContentInstaller):
    def can_install(self, content: Content) -> bool:
        return content.content_type == "workflow"

    async def install(self, content: Content) -> InstallationResult:

        with open(content.path / "workflow.json", "r") as f:
            workflow = json.load(f)

        with open(content.path / "workflow_definition.py", "r", encoding="utf-8") as f:
            workflow_definition = f.read()
            workflow["definition"] = workflow_definition

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://workflow-api.services.svc:80/v1/workflows",
                json=workflow,
            )
            response.raise_for_status()

        return InstallationResult(
            success=True,
            message=f"Workflow installed with status code {response.status_code}",
        )

    async def uninstall(self, content: Content) -> None:
        print(f"Uninstalling workflow")
