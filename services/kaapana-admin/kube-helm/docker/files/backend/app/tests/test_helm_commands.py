"""Checks that each untrusted value reaches helm, kubectl or ctr as exactly one argument."""

import yaml

from app import helm_helper, utils


def test_helm_status_passes_release_name_as_one_argument(fake_cli, marker):
    payload = f"demo; touch {marker}"

    assert utils.helm_status(payload, helm_namespace="admin") == {}

    assert fake_cli.calls() == [["-n", "admin", "status", "-o", "yaml", payload]]
    assert not marker.exists()


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
    payload = f"demo; touch {marker}"

    assert helm_helper.helm_get_values(payload, helm_namespace="admin") == {}

    assert fake_cli.calls() == [["-n", "admin", "get", "values", "--all", "-o", "json", payload]]
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
    release_name = f"demo; touch {marker}"

    success, _, _, _ = helm_helper.get_kube_objects(release_name, helm_namespace="admin")

    assert success
    assert fake_cli.calls() == [["-n", "admin", "get", "manifest", release_name]]
    assert fake_cli.calls("kubectl") == [["-n", namespace, "get", "pod", f"-l=app.kubernetes.io/name={app_name}"]]
    assert not marker.exists()


def test_helm_show_chart_and_values_pass_chart_path_as_one_argument(fake_cli, marker):
    from app.config import settings

    name = f"demo; touch {marker}"
    chart_path = f"{settings.helm_extensions_cache}/{name}-0.1.0.tgz"

    helm_helper.helm_show_chart(name=name, version="0.1.0")
    helm_helper.helm_show_values(name=name, version="0.1.0")
    helm_helper.helm_show_chart(package=chart_path)

    assert fake_cli.calls() == [
        ["show", "chart", chart_path],
        ["show", "values", chart_path],
        ["show", "chart", chart_path],
    ]
    assert not marker.exists()


def test_collect_helm_deployments_passes_namespace_as_one_argument(fake_cli, marker):
    namespace = f"admin; touch {marker}"

    helm_helper.collect_helm_deployments(helm_namespace=namespace)
    utils.collect_helm_deployments(helm_namespace=namespace)

    calls = fake_cli.calls()
    assert len(calls) == 2
    assert all(call[call.index("-n") + 1] == namespace for call in calls)
    assert not marker.exists()
