import httpx
import pytest
from v1.services.dispatch.consumers import workflows
from v1.services.dispatch.consumers.workflows import WorkflowInstaller
from v1.services.dispatch.content import Content
from v1.services.dispatch.exceptions import ConsumerError

LOCATION = "/workflows/4c3d0000-0000-0000-0000-000000000000"


@pytest.fixture
def workflow_api(monkeypatch):
    requests = []
    responses = {"status_code": 204}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(responses["status_code"], text="error")

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        workflows.httpx,
        "AsyncClient",
        lambda: real_client(transport=httpx.MockTransport(handler)),
    )
    return requests, responses


def _content() -> Content:
    return Content(name="seg", content_type="workflow-v1", location=LOCATION)


@pytest.mark.asyncio
async def test_uninstall_deletes_workflow(workflow_api):
    requests, _ = workflow_api

    await WorkflowInstaller().uninstall(_content())

    assert [(r.method, r.url.path) for r in requests] == [("DELETE", f"/v1{LOCATION}")]


@pytest.mark.asyncio
async def test_uninstall_accepts_workflow_that_is_already_gone(workflow_api):
    _, responses = workflow_api
    responses["status_code"] = 404

    await WorkflowInstaller().uninstall(_content())


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 409, 500, 503])
async def test_uninstall_fails_on_other_errors(workflow_api, status_code):
    _, responses = workflow_api
    responses["status_code"] = status_code

    with pytest.raises(ConsumerError):
        await WorkflowInstaller().uninstall(_content())
