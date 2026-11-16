"""Sends untrusted values through the real middleware and router."""

import json

import pytest

PROJECT_HEADERS = {"Project": json.dumps({"id": "project-id", "name": "project"})}


@pytest.fixture
def aii(monkeypatch):
    """Replaces the project lookups in the access-information-interface."""
    from app import routes

    whitelist = ["demo-chart"]

    async def fetch_whitelist(project_id):
        return whitelist

    async def fetch_project(project_id):
        return {
            "id": project_id,
            "name": "project",
            "short_id": "abcd1234",
            "kubernetes_namespace": "project-abcd1234",
        }

    monkeypatch.setattr(routes, "_fetch_project_whitelist", fetch_whitelist)
    monkeypatch.setattr(routes, "_fetch_project", fetch_project)
    return whitelist


def install(client, headers=None, **payload):
    body = {"name": "demo-chart", "version": "0.1.0", **payload}
    return client.post("/helm-install-chart", headers=headers or {}, json=body)


def test_complete_active_application_runs_no_injected_command(client, fake_cli, marker):
    payload = f"x; touch {marker}; #"

    response = client.post("/complete-active-application", json={"release_name": payload})

    assert response.status_code == 500
    (call,) = fake_cli.calls()
    assert f"--filter={payload}" in call
    assert not marker.exists()


def test_view_chart_status_passes_release_name_as_one_argument(client, fake_cli):
    response = client.get("/view-chart-status", params={"release_name": "demo --all"})

    assert response.status_code == 404
    assert fake_cli.calls() == [["-n", "default", "status", "-o", "yaml", "demo --all"]]


def test_install_release_name_runs_no_injected_command(client, fake_cli, aii, marker):
    release_name = f"x; touch {marker}; true"

    response = install(client, PROJECT_HEADERS, keywords=["kaapanaapplication"], release_name=release_name)

    assert response.status_code == 200
    (call,) = fake_cli.calls_with("install")
    assert call[-2] == release_name
    assert not marker.exists()


def test_install_set_key_runs_no_injected_command(client, fake_cli, aii, marker):
    set_key = f"a$(touch {marker})"

    response = install(client, PROJECT_HEADERS, keywords=["kaapanaapplication"], sets={set_key: "v"})

    assert response.status_code == 200
    (call,) = fake_cli.calls_with("install")
    assert f"--set-string={set_key}=v" in call
    assert not marker.exists()


def test_install_keyword_with_quote_runs_no_injected_command(client, fake_cli, aii, marker):
    keyword = f"k'$(touch {marker})'"

    response = install(client, PROJECT_HEADERS, keywords=["kaapanaapplication", keyword])

    assert response.status_code == 200
    assert not marker.exists()


def test_delete_release_name_runs_no_injected_command(client, fake_cli, marker):
    release_name = f"x; touch {marker}; true"

    response = client.post("/helm-delete-chart", json={"release_name": release_name, "helm_command_addons": ""})

    assert response.status_code == 200
    assert fake_cli.wait_for_calls("uninstall") == [["-n", "default", "uninstall", release_name]]
    assert not marker.exists()
