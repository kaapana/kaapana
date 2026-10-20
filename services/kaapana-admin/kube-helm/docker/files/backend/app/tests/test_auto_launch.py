# Runs app/auto_launch.py with its helm, AII and settings boundary stubbed out, so
# the per-project reconcile can be checked offline.
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / "auto_launch.py"
PROJECTS = [
    {"id": s, "name": n, "short_id": s, "kubernetes_namespace": f"ns-{s}"}
    for n, s in [("admin", "admin"), ("p1", "aaaa1111"), ("p2", "bbbb2222")]
]


def reconcile(apps, exclude_projects='["admin"]'):
    """One reconcile pass over PROJECTS, where p1 already has the release
    sync-aaaa1111; returns the install payloads."""
    installed = []
    app = ModuleType("app")
    app.helm_helper = SimpleNamespace(
        CHART_STATUS_DEPLOYED="deployed", helm_show_chart=lambda **k: {}
    )
    app.utils = SimpleNamespace(
        get_helm_status_name=lambda *a: "deployed",
        collect_helm_deployments=lambda: {"sync-1": [{"name": "sync-aaaa1111"}]},
        helm_install=lambda payload, **k: installed.append(payload),
    )
    settings = SimpleNamespace(
        release_name="platform",
        aii_service_url="http://aii",
        auto_launch_project_apps=apps,
        auto_launch_exclude_projects=exclude_projects,
    )
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: PROJECTS)
    stubs = {
        "app": app,
        "app.config": SimpleNamespace(settings=settings),
        "app.repeat_timer": SimpleNamespace(RepeatedTimer=None),
        "httpx": SimpleNamespace(get=lambda *a, **k: response),
        "kaapanapy": SimpleNamespace(),
        "kaapanapy.logger": SimpleNamespace(get_logger=lambda _: mock.Mock()),
    }
    with mock.patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location("app.auto_launch", MODULE)
        auto_launch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auto_launch)
        auto_launch.reconcile_project_apps()
    return installed


def test_reconcile_installs_app_only_for_projects_without_one():
    # p1 already has its release and admin is excluded, so only p2 gets an
    # install, carrying its own project context (#2264).
    installed = reconcile('[{"name": "sync", "version": "1"}]')
    assert [p["release_name"] for p in installed] == ["sync-bbbb2222"]
    assert installed[0]["extension_params"]["project_namespace"] == "ns-bbbb2222"


def test_an_apps_own_exclude_list_replaces_the_default():
    # "login" names no project to skip, so it reaches admin as well; "sync" keeps
    # the default list. The key is the reconciler's, not a chart parameter.
    installed = reconcile(
        '[{"name": "sync", "version": "1"},'
        ' {"name": "login", "version": "1", "exclude_projects": []}]'
    )
    assert [p["release_name"] for p in installed] == [
        "sync-bbbb2222",
        "login-admin",
        "login-aaaa1111",
        "login-bbbb2222",
    ]
    assert all("exclude_projects" not in p["extension_params"] for p in installed)
