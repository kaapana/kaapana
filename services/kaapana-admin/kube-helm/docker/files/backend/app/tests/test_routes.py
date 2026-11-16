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


def test_complete_active_application_rejects_invalid_release_name(client, fake_cli, marker):
    response = client.post("/complete-active-application", json={"release_name": f"x; touch {marker}; #"})

    assert response.status_code == 400
    assert fake_cli.calls() == []
    assert not marker.exists()


def test_complete_active_application_passes_filter_as_one_argument(client, fake_cli):
    response = client.post("/complete-active-application", json={"release_name": "demo"})

    assert response.status_code == 500
    (call,) = fake_cli.calls()
    assert "--filter=demo" in call


def test_view_chart_status_does_not_pass_invalid_names_to_helm(client, fake_cli):
    response = client.get("/view-chart-status", params={"release_name": "demo --all"})

    assert response.status_code == 404
    assert fake_cli.calls() == []


def test_install_rejects_invalid_release_name(client, fake_cli, aii, marker):
    release_name = f"x; touch {marker}; true"

    response = install(client, PROJECT_HEADERS, keywords=["kaapanaapplication"], release_name=release_name)

    assert response.status_code == 400
    assert fake_cli.calls_with("install") == []
    assert not marker.exists()


def test_install_rejects_invalid_set_key(client, fake_cli, aii, marker):
    response = install(client, PROJECT_HEADERS, keywords=["kaapanaapplication"], sets={f"a$(touch {marker})": "v"})

    assert response.status_code == 400
    assert fake_cli.calls_with("install") == []
    assert not marker.exists()


def test_install_ignores_keywords_from_the_request(client, fake_cli, aii, marker):
    response = install(client, PROJECT_HEADERS, keywords=["kaapanaint", f"k'$(touch {marker})'"])

    assert response.status_code == 200
    (call,) = fake_cli.calls_with("install")
    assert "--labels=kaapana.ai/kaapanaapplication=True" in call
    assert not marker.exists()


def test_install_checks_the_whitelist_with_the_keywords_of_the_chart(client, fake_cli, aii):
    fake_cli.respond(
        ["show", "chart"],
        stdout="name: demo-chart\nversion: 0.1.0\nkeywords:\n- kaapanaapplication\n- kaapanamultiinstallable\n",
    )
    aii[:] = ["other-chart"]

    response = install(client, PROJECT_HEADERS, keywords=["kaapanaapplication"])

    assert response.status_code == 403
    assert fake_cli.calls_with("install") == []


def test_install_passes_set_value_as_one_argument(client, fake_cli, aii, marker):
    value = f"$(touch {marker})"

    response = install(client, PROJECT_HEADERS, keywords=["kaapanaapplication"], sets={"global.text": value})

    assert response.status_code == 200
    (call,) = fake_cli.calls_with("install")
    assert f"--set-string=global.text={value.replace(' ', '')}" in call
    assert not marker.exists()


def test_delete_rejects_invalid_release_name(client, fake_cli, marker):
    release_name = f"x; touch {marker}; true"

    response = client.post("/helm-delete-chart", json={"release_name": release_name, "helm_command_addons": ""})

    assert response.status_code == 400
    assert fake_cli.calls_with("uninstall") == []
    assert not marker.exists()


@pytest.mark.parametrize("addons, expected", [("", []), ("--no-hooks", ["--no-hooks"])])
def test_delete_accepts_the_known_command_addons(client, fake_cli, addons, expected):
    response = client.post("/helm-delete-chart", json={"release_name": "demo", "helm_command_addons": addons})

    assert response.status_code == 200
    assert fake_cli.wait_for_calls("uninstall") == [["-n", "default", "uninstall", *expected, "--", "demo"]]


@pytest.mark.parametrize("addons", ["--dry-run", "--no-hooks --wait", ["--no-hooks"]])
def test_delete_rejects_other_command_addons(client, fake_cli, addons):
    response = client.post("/helm-delete-chart", json={"release_name": "demo", "helm_command_addons": addons})

    assert response.status_code == 400
    assert fake_cli.calls_with("uninstall") == []


def test_image_pull_ignores_fields_other_than_the_image(client, fake_cli, marker, monkeypatch):
    from app.config import settings, timeouts

    monkeypatch.setattr(timeouts, "helm_pull_uninstall_delay", 0)
    with open(f"{settings.helm_helpers_cache}/pull-docker-chart-0.1.0.tgz", "wb"):
        pass

    response = client.post(
        "/pull-docker-image",
        json={
            "docker_registry_url": "registry.example.com",
            "docker_image": "image",
            "docker_version": "1.0.0",
            "helm_namespace": f"admin; touch {marker};",
            "blocking": True,
        },
    )

    assert response.status_code == 202
    (uninstall,) = fake_cli.wait_for_calls("uninstall")
    (install,) = fake_cli.calls_with("install")
    assert install[:2] == uninstall[:2] == ["-n", "default"]
    assert not marker.exists()


def test_container_import_rejects_paths(client, fake_cli):
    response = client.get("/import-container", params={"filename": "../extensions/image.tar"})

    assert response.status_code == 400
    assert fake_cli.calls("ctr") == []


def test_container_import_runs_no_injected_command(client, fake_cli, marker, monkeypatch):
    from app.config import settings

    monkeypatch.chdir(marker.parent)
    filename = f"image.tar; touch {marker.name}"
    open(f"{settings.helm_extensions_cache}/{filename}", "wb").close()

    response = client.get("/import-container", params={"filename": filename})

    assert response.status_code == 200
    (call,) = fake_cli.calls("ctr")
    assert call[-1] == f"{settings.helm_extensions_cache}/{filename}"
    assert not marker.exists()
