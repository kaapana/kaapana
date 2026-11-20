"""NotificationService.send must not fail when there is nobody to notify.

The notification-service answers 422 for a project that has only system users
and 404 for an unknown project or user. Those are expected outcomes, so
``send`` logs a warning and returns. Every other error is still raised.
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
    """Fake notification-service: map URL -> status code, record every call."""
    routes: dict[str, int] = {}
    calls: list[dict] = []

    def fake_post(url, json):
        calls.append({"url": url, "json": dict(json)})
        return make_response(routes[url])

    monkeypatch.setattr(ns_module.requests, "post", fake_post)
    return routes, calls


# --- project-wide path (no user_ids) ---------------------------------------


@pytest.mark.parametrize("status", [404, 422])
def test_project_without_receivers_does_not_raise(server, status, caplog):
    routes, calls = server
    routes[f"{BASE}/v2/{PROJECT_ID}"] = status

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID)

    assert len(calls) == 1
    assert "Notification not sent" in caplog.text


def test_project_success(server):
    routes, calls = server
    routes[f"{BASE}/v2/{PROJECT_ID}"] = 200

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID)

    assert [c["url"] for c in calls] == [f"{BASE}/v2/{PROJECT_ID}"]


@pytest.mark.parametrize("status", [500, 502])
def test_project_server_error_is_raised(server, status):
    routes, _ = server
    routes[f"{BASE}/v2/{PROJECT_ID}"] = status

    with pytest.raises(requests.exceptions.HTTPError):
        NotificationService.send(NOTIFICATION, project_id=PROJECT_ID)


# --- per-user path ----------------------------------------------------------


@pytest.mark.parametrize("status", [404, 422])
def test_user_falls_back_to_send_without_project_context(server, status):
    """A user that can't be reached in the project context still gets the notification."""
    routes, calls = server
    routes[f"{BASE}/v2/{PROJECT_ID}/{USER_ID}"] = status
    routes[f"{BASE}/v2/"] = 200

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID, user_ids=[USER_ID])

    assert [c["url"] for c in calls] == [
        f"{BASE}/v2/{PROJECT_ID}/{USER_ID}",
        f"{BASE}/v2/",
    ]
    assert calls[1]["json"]["receivers"] == [USER_ID]


def test_user_success_has_no_fallback(server):
    routes, calls = server
    routes[f"{BASE}/v2/{PROJECT_ID}/{USER_ID}"] = 200

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID, user_ids=[USER_ID])

    assert len(calls) == 1


def test_unknown_user_in_fallback_does_not_raise(server, caplog):
    routes, _ = server
    routes[f"{BASE}/v2/{PROJECT_ID}/{USER_ID}"] = 422
    routes[f"{BASE}/v2/"] = 404

    NotificationService.send(NOTIFICATION, project_id=PROJECT_ID, user_ids=[USER_ID])

    assert "unknown receivers" in caplog.text


def test_user_server_error_is_raised(server):
    routes, _ = server
    routes[f"{BASE}/v2/{PROJECT_ID}/{USER_ID}"] = 500

    with pytest.raises(requests.exceptions.HTTPError):
        NotificationService.send(NOTIFICATION, project_id=PROJECT_ID, user_ids=[USER_ID])


def test_fallback_server_error_is_raised(server):
    routes, _ = server
    routes[f"{BASE}/v2/{PROJECT_ID}/{USER_ID}"] = 422
    routes[f"{BASE}/v2/"] = 500

    with pytest.raises(requests.exceptions.HTTPError):
        NotificationService.send(NOTIFICATION, project_id=PROJECT_ID, user_ids=[USER_ID])
