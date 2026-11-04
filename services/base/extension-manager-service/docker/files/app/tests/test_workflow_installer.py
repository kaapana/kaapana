import json
import shutil
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from v1.services.dispatch import Content, Dispatcher, WorkflowInstaller
from v1.services.dispatch.exceptions import ConsumerError, ContentError

MOCK_WORKFLOW_DIR = Path(__file__).resolve().parents[1] / "v1" / "mock_data" / "extension-v1" / "mock-workflow"
LOCATION = "/workflows/0b6c2a54-3f0e-4c55-9a43-6f1e7c0f6a10"

AsyncClient = httpx.AsyncClient


@pytest.fixture
def workflow_dir(tmp_path: Path) -> Path:
    target = tmp_path / "mock-workflow"
    shutil.copytree(MOCK_WORKFLOW_DIR, target)
    workflow_file = target / "workflow.json"
    workflow = json.loads(workflow_file.read_text())
    workflow["labels"].append({"key": "kaapana.extension.version", "value": "0.0.1"})
    workflow_file.write_text(json.dumps(workflow))
    return target


def _content(path: Path | None, location: str | None = LOCATION) -> Content:
    return Content(
        name="mock-workflow",
        content_type="workflow-v1",
        path=path,
        location=location,
        extension_id=uuid4(),
        extension_name="mock-workflow-extension",
        extension_version="2.0.0",
    )


def _respond_with(status_code: int, requests: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, headers={"Location": LOCATION})

    transport = httpx.MockTransport(handler)
    return patch(
        "v1.services.dispatch.consumers.workflows.httpx.AsyncClient",
        new=lambda *args, **kwargs: AsyncClient(transport=transport),
    )


async def test_update_patches_the_installed_workflow(workflow_dir: Path):
    requests: list[httpx.Request] = []
    content = _content(workflow_dir)

    with _respond_with(200, requests):
        result = await WorkflowInstaller().update(content)

    assert result.location == LOCATION
    [request] = requests
    assert request.method == "PATCH"
    assert request.url.path == f"/v1{LOCATION}"
    body = json.loads(request.content)
    assert "workflow_engine" not in body
    assert body["definition"] == (workflow_dir / "workflow_definition.py").read_text()
    labels = {label["key"]: label["value"] for label in body["labels"]}
    assert len(labels) == len(body["labels"])
    assert labels["kaapana.immutable.extension.id"] == str(content.extension_id)
    assert labels["kaapana.immutable.extension.content_name"] == "mock-workflow"
    assert labels["kaapana.extension.version"] == "2.0.0"
    assert labels["category"] == "testing"


async def test_update_failure_raises_consumer_error(workflow_dir: Path):
    with _respond_with(422, []), pytest.raises(ConsumerError):
        await WorkflowInstaller().update(_content(workflow_dir))


async def test_install_still_sends_the_workflow_engine(workflow_dir: Path):
    requests: list[httpx.Request] = []

    with _respond_with(201, requests):
        result = await WorkflowInstaller().install(_content(workflow_dir, location=None))

    assert result.location == LOCATION
    [request] = requests
    assert request.method == "POST"
    assert json.loads(request.content)["workflow_engine"] == "airflow"


async def test_dispatcher_rejects_an_update_without_location(workflow_dir: Path):
    dispatcher = Dispatcher(installers=[WorkflowInstaller()])

    with pytest.raises(ContentError):
        await dispatcher.update_content(_content(workflow_dir, location=None))
