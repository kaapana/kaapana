"""Checks that each untrusted value reaches helm, kubectl or ctr as exactly one argument."""

import asyncio
import json
from types import SimpleNamespace

import pytest
import yaml

from app import file_handler, helm_helper, utils, validation
from app.config import settings, timeouts


def test_helm_status_passes_release_name_after_end_of_options(fake_cli):
    assert utils.helm_status("demo", helm_namespace="admin") == {}

    assert fake_cli.calls() == [["-n", "admin", "status", "-o", "yaml", "--", "demo"]]


def test_helm_status_does_not_call_helm_for_invalid_release_names(fake_cli, marker):
    assert utils.helm_status(f"demo; touch {marker}") == {}
    assert utils.helm_status("--all") == {}

    assert fake_cli.calls() == []


def test_helm_ls_passes_each_filter_as_one_argument(fake_cli, marker):
    payload = f"demo; touch {marker}; #"

    assert utils.helm_ls(release_filter=payload, label_filter="kaapana.ai/kaapanaint=True") == []

    (call,) = fake_cli.calls()
    assert f"--filter={payload}" in call
    assert "--selector=kaapana.ai/kaapanaint=True" in call
    assert not marker.exists()


def test_helm_ls_returns_releases(fake_cli):
    fake_cli.respond(["ls"], stdout='[{"name": "demo"}]')

    assert utils.helm_ls(release_filter="demo") == [{"name": "demo"}]


def test_helm_get_values_passes_release_name_as_one_argument(fake_cli, marker):
    payload = f"--demo; touch {marker}"

    assert helm_helper.helm_get_values(payload, helm_namespace="admin") == {}

    assert fake_cli.calls() == [["-n", "admin", "get", "values", "--all", "-o", "json", "--", payload]]
    assert not marker.exists()


def test_get_kube_objects_passes_names_as_one_argument(fake_cli, marker):
    app_name = f"app; touch {marker}"
    namespace = f"ns $(touch {marker})"
    manifest = {
        "kind": "Deployment",
        "metadata": {"name": "demo", "namespace": namespace},
        "spec": {"selector": {"matchLabels": {"app.kubernetes.io/name": app_name}}},
    }
    fake_cli.respond(["get", "manifest"], stdout=yaml.safe_dump(manifest))
    fake_cli.respond(["get", "pod"], stdout="NAME   READY   STATUS   RESTARTS   AGE\n")
    release_name = f"--demo; touch {marker}"

    success, _, _, _ = helm_helper.get_kube_objects(release_name, helm_namespace="admin")

    assert success
    assert fake_cli.calls() == [["-n", "admin", "get", "manifest", "--", release_name]]
    assert fake_cli.calls("kubectl") == [["-n", namespace, "get", "pod", f"-l=app.kubernetes.io/name={app_name}"]]
    assert not marker.exists()


def test_helm_show_chart_and_values_pass_chart_path_as_one_argument(fake_cli, marker):
    name = f"demo; touch {marker}"
    chart_path = f"{settings.helm_extensions_cache}/{name}-0.1.0.tgz"

    helm_helper.helm_show_chart(name=name, version="0.1.0")
    helm_helper.helm_show_values(name=name, version="0.1.0")
    helm_helper.helm_show_chart(package=chart_path)

    assert fake_cli.calls() == [
        ["show", "chart", "--", chart_path],
        ["show", "values", "--", chart_path],
        ["show", "chart", "--", chart_path],
    ]
    assert not marker.exists()


def test_helm_show_chart_and_values_stay_inside_the_cache(fake_cli):
    assert helm_helper.helm_show_chart(name="../../outside", version="0.1.0") == {}
    assert helm_helper.helm_show_values(name="../../outside", version="0.1.0") == {}

    assert fake_cli.calls() == []


def test_collect_helm_deployments_passes_namespace_as_one_argument(fake_cli, marker):
    namespace = f"admin; touch {marker}"

    helm_helper.collect_helm_deployments(helm_namespace=namespace)
    utils.collect_helm_deployments(helm_namespace=namespace)

    calls = fake_cli.calls()
    assert len(calls) == 2
    assert all(call[call.index("-n") + 1] == namespace for call in calls)
    assert not marker.exists()


def test_helm_set_arguments_escape_values_for_helm():
    arguments = helm_helper.helm_set_arguments(
        {
            "global.text": "a,b {c} d'e",
            "global.pattern": r".*\.dcm",
            "global.list": ["a", "b", 1],
            "global.number": 5,
        }
    )

    assert arguments == [
        r"--set-string=global.text=a\,b\{c\}d'e",
        r"--set-string=global.pattern=.*\\.dcm",
        "--set=global.list={a,b,1}",
        "--set=global.number=5",
    ]


def test_helm_set_arguments_keep_each_value_inside_its_key():
    arguments = helm_helper.helm_set_arguments(
        {
            "global.text": r"x\,global.injected=yes",
            "global.list": ["a},global.injected=yes,global.m={b"],
            "global.object": {"k": "1},global.injected=yes"},
        }
    )

    assert arguments == [
        r"--set-string=global.text=x\\\,global.injected=yes",
        r"--set=global.list={a\}\,global.injected=yes\,global.m=\{b}",
        r"--set-string=global.object=\{'k':'1\}\,global.injected=yes'\}",
    ]


def test_install_command_passes_each_value_as_one_argument(fake_cli, marker):
    value = f"$(touch {marker})"
    payload = {
        "name": "demo-chart",
        "version": "0.1.0-12-gabc",
        "release_name": "demo",
        "keywords": ["kaapanaapplication", "kaapanaworkflow"],
        "sets": {"global.text": value},
        "extension_params": {"display_name": value},
    }

    success, _, _, _, _ = utils.helm_install(payload)

    assert success
    (call,) = fake_cli.calls_with("install")
    assert call[:3] == ["-n", "default", "install"]
    assert f"--set-string=global.text={value.replace(' ', '')}" in call
    assert f"--set-string=global.display_name={value.replace(' ', '')}" in call
    assert "--labels=kaapana.ai/kaapanaapplication=True,kaapana.ai/kaapanaworkflow=True" in call
    assert call[-3:] == ["--", "demo", f"{settings.helm_extensions_cache}/demo-chart-0.1.0-12-gabc.tgz"]
    assert not marker.exists()


@pytest.mark.parametrize(
    "change",
    [
        {"release_name": "x; touch marker"},
        {"release_name": "--dry-run"},
        {"name": "../demo-chart"},
        {"version": "0.1.0/../../x"},
        {"sets": {"a,b": "v"}},
        {"sets": {"-a": "v"}},
        {"extension_params": {"a=b": "v"}},
        {"keywords": ["kaapanaapplication", "a=b,c"]},
        {"sets": {"global.helm_namespace": "ns; touch marker"}},
    ],
)
def test_install_rejects_invalid_values(fake_cli, change):
    payload = {"name": "demo-chart", "version": "0.1.0", "keywords": ["kaapanaapplication"], **change}

    with pytest.raises(validation.InvalidValueError):
        utils.helm_install(payload)

    assert fake_cli.calls_with("install") == []


def test_reinstall_of_a_collection_uses_argument_lists(fake_cli, monkeypatch):
    monkeypatch.setattr(settings, "kaapana_collections", "registry.example.com/demo-collection:1.0.0;")
    fake_cli.respond(["status"], stdout="info:\n  status: deployed\n")

    install_error, _ = utils.execute_update_extensions()

    assert not install_error
    (uninstall,) = fake_cli.calls_with("uninstall")
    assert uninstall[:5] == ["-n", "default", "uninstall", "--wait", "--timeout=5m"]
    (install,) = fake_cli.calls_with("install")
    assert "--wait" in install
    assert "--set-string=kube_helm_collection=registry.example.com/demo-collection:1.0.0" in install


def test_upload_check_passes_chart_name_as_one_argument(fake_cli, marker):
    name = f"demo; touch {marker}"
    fake_cli.respond(["show", "chart"], stdout=yaml.safe_dump({"name": name, "version": "0.1.0"}))
    fake_cli.respond(
        ["get", "values"],
        stdout=json.dumps({"global": {"admin_namespace": "admin", "registry_url": "a b,c"}}),
    )

    assert file_handler.check_file_namespace("demo-0.1.0.tgz")

    (call,) = fake_cli.calls_with("--dry-run")
    assert call == [
        "install",
        "--set-string=global.admin_namespace=admin",
        r"--set-string=global.registry_url=ab\,c",
        "-o",
        "json",
        "--dry-run",
        "--",
        name,
        f"{settings.helm_extensions_cache}/demo-0.1.0.tgz",
    ]
    assert not marker.exists()


@pytest.mark.parametrize("platforms", [False, True])
def test_uninstall_command_is_an_argument_list(fake_cli, platforms):
    success, _ = utils.helm_delete(
        release_name="demo",
        helm_namespace="admin",
        helm_command_addons=["--no-hooks"],
        platforms=platforms,
    )

    assert success
    assert fake_cli.wait_for_calls("uninstall") == [["-n", "admin", "uninstall", "--no-hooks", "--", "demo"]]


@pytest.mark.parametrize(
    "release_name, namespace",
    [("x; touch marker", "admin"), ("--all", "admin"), ("demo", "admin $(touch marker)")],
)
def test_uninstall_rejects_invalid_values(fake_cli, release_name, namespace):
    with pytest.raises(validation.InvalidValueError):
        utils.helm_delete(release_name=release_name, helm_namespace=namespace)
    with pytest.raises(validation.InvalidValueError):
        utils.run_supervised_uninstall(release_name, namespace, utils.CHART_STATUS_FAILED)

    assert fake_cli.calls_with("uninstall") == []


def test_supervised_uninstall_uses_argument_lists(fake_cli, monkeypatch):
    monkeypatch.setattr(timeouts, "helm_release_status_check_interval", 0)
    fake_cli.respond(["status"], stdout="info:\n  status: uninstalling\n")

    success, _ = utils.run_supervised_uninstall("demo", "admin", utils.CHART_STATUS_UNINSTALLING)

    assert not success
    assert fake_cli.calls_with("uninstall") == [
        ["-n", "admin", "uninstall", "--wait", f"--timeout={timeouts.helm_deletion_timeout}s", "--", "demo"],
        ["-n", "admin", "uninstall", "--no-hooks", "--", "demo"],
    ]


@pytest.fixture
def pull_chart(fake_cli, monkeypatch):
    monkeypatch.setattr(timeouts, "helm_pull_uninstall_delay", 0)
    chart = f"{settings.helm_helpers_cache}/pull-docker-chart-0.1.0.tgz"
    with open(chart, "wb"):
        pass
    return chart


def test_image_pull_installs_and_then_uninstalls_without_a_shell(fake_cli, pull_chart, marker):
    image = f"image; touch {marker}"

    success, _ = utils.pull_docker_image(
        "pull-docker-chart-0123",
        docker_image=image,
        docker_version="1.0.0",
        docker_registry_url="registry.example.com",
        blocking=True,
    )

    assert success
    install, uninstall = fake_cli.calls()[-2:]
    assert install[:3] == ["-n", "default", "install"]
    assert f"--set-string=image={image.replace(' ', '')}" in install
    assert ["--wait", "--atomic", f"--timeout={timeouts.helm_pull_container_timeout}s"] == [
        argument for argument in install if argument in ("--wait", "--atomic") or argument.startswith("--timeout")
    ]
    assert install[-3:] == ["--", "pull-docker-chart-0123", pull_chart]
    assert uninstall == ["-n", "default", "uninstall", "--", "pull-docker-chart-0123"]
    assert not marker.exists()


def test_image_pull_reports_a_failed_uninstall(fake_cli, pull_chart):
    fake_cli.respond(["uninstall"], code=1)

    success, _ = utils.pull_docker_image(
        "pull-docker-chart-0123",
        docker_image="image",
        docker_version="1.0.0",
        docker_registry_url="registry.example.com",
        blocking=True,
    )

    assert not success


def test_non_blocking_image_pull_uninstalls_in_the_background(fake_cli, pull_chart):
    success, _ = utils.pull_docker_image(
        "pull-docker-chart-0123",
        docker_image="image",
        docker_version="1.0.0",
        docker_registry_url="registry.example.com",
    )

    assert success
    assert fake_cli.wait_for_calls("uninstall") == [["-n", "default", "uninstall", "--", "pull-docker-chart-0123"]]
    assert [call[2] for call in fake_cli.calls_with("pull-docker-chart-0123")][-2:] == ["install", "uninstall"]


def test_container_import_passes_file_path_as_one_argument(fake_cli, marker, monkeypatch):
    # A relative path lets the injected command reach the marker without a slash in the file name.
    monkeypatch.chdir(marker.parent)
    filename = f"image.tar; touch {marker.name}"
    open(f"{settings.helm_extensions_cache}/{filename}", "wb").close()

    success, _ = asyncio.run(file_handler.run_containerd_import(filename))

    assert success
    assert fake_cli.calls("ctr") == [
        [
            "--namespace",
            "k8s.io",
            f"--address={settings.containerd_sock}",
            "image",
            "import",
            "--digests",
            f"{settings.helm_extensions_cache}/{filename}",
        ]
    ]
    assert not marker.exists()


@pytest.mark.parametrize("filename", ["../image.tar", "/tmp/image.tar", "..", ""])
def test_container_import_rejects_paths(fake_cli, filename):
    with pytest.raises(validation.InvalidValueError):
        asyncio.run(file_handler.run_containerd_import(filename))

    assert fake_cli.calls("ctr") == []


def test_chart_upload_passes_file_path_as_one_argument(fake_cli, marker, monkeypatch):
    monkeypatch.chdir(marker.parent)
    upload = SimpleNamespace(filename=f"demo; touch {marker.name}-0.1.0.tgz", content_type="application/gzip")

    success, _ = file_handler.add_file(upload, b"chart")

    assert success
    assert fake_cli.calls() == [["show", "chart", "--", f"{settings.helm_extensions_cache}/{upload.filename}"]]
    assert not marker.exists()
