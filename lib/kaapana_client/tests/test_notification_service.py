"""NotificationService.send must never fail the calling task (issue #2233).

Notifications are a non-critical side effect: any error (e.g. 422 for a project
that has only system users, 404, server or connection errors) is logged as a
warning and ``send`` returns normally.
"""

import pytest
import requests
from kaapana_client.services import NotificationService as ns_module
from kaapana_client.services.NotificationService import Notification, NotificationService

PROJECT_ID = "63e83595-ff7c-496a-b254-84d3d777fc7a"
USER_ID = "b1c2d3e4-0000-0000-0000-000000000001"
BASE = ns_module.NOTIFICATION_SERVICE_URL
NOTIFICATION = Notification(title="Model download", description="finished")


def make_response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = b'{"detail": "test"}'
    response.url = "http://notification-service.test"
    return response


@pytest.fixture
def server(monkeypatch):
    """Fake notification-service.

    ``routes`` maps URL -> status code, or -> an exception the request raises.
    Every call is recorded.
    """
    routes: dict[str, int | Exception] = {}
    calls: list[dict] = []

    def fake_post(url, json):
        calls.append({"url": url, "json": dict(json)})
        answer = routes[url]
        if isinstance(answer, Exception):
            raise answer
        return make_response(answer)

    monkeypatch.setattr(ns_module.requests, "post", fake_post)
    return routes, calls


def test_project_success(server):
    routes, calls = server
    routes[f"{BASE}/v2/{PROJECT_ID}"] = 200

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID)

    assert [c["url"] for c in calls] == [f"{BASE}/v2/{PROJECT_ID}"]


@pytest.mark.parametrize(
    "answer",
    [404, 422, 500, requests.exceptions.ConnectionError("service down")],
)
def test_project_error_is_logged_not_raised(server, answer, caplog):
    routes, _ = server
    routes[f"{BASE}/v2/{PROJECT_ID}"] = answer

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID)

    assert "Failed to send notification" in caplog.text


def test_user_not_in_project_falls_back_to_send_without_project_context(server):
    routes, calls = server
    routes[f"{BASE}/v2/{PROJECT_ID}/{USER_ID}"] = 404
    routes[f"{BASE}/v2/"] = 200

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID, user_ids=[USER_ID])

    assert [c["url"] for c in calls] == [f"{BASE}/v2/{PROJECT_ID}/{USER_ID}", f"{BASE}/v2/"]
    assert calls[1]["json"]["receivers"] == [USER_ID]


@pytest.mark.parametrize(
    "user_answer, fallback_answer",
    [(422, None), (500, None), (404, 404), (404, 500)],
)
def test_user_error_is_logged_not_raised(server, user_answer, fallback_answer, caplog):
    routes, _ = server
    routes[f"{BASE}/v2/{PROJECT_ID}/{USER_ID}"] = user_answer
    routes[f"{BASE}/v2/"] = fallback_answer

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID, user_ids=[USER_ID])

    assert "Failed to send notification" in caplog.text
