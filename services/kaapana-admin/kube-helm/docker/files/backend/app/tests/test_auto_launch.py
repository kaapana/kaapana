# Runs app/auto_launch.py with its helm, AII and settings boundary stubbed out, so
# the per-project reconcile can be checked offline.
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / "auto_launch.py"


def test_reconcile_installs_app_only_for_projects_without_one():
    # p1 already has its release and admin is excluded, so only p2 gets an
    # install, carrying its own project context (#2264).
    projects = [
        {"id": s, "name": n, "short_id": s, "kubernetes_namespace": f"ns-{s}"}
        for n, s in [("admin", "admin"), ("p1", "aaaa1111"), ("p2", "bbbb2222")]
    ]
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
        auto_launch_project_apps='[{"name": "sync", "version": "1"}]',
        auto_launch_exclude_projects='["admin"]',
    )
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: projects)
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
    assert [p["release_name"] for p in installed] == ["sync-bbbb2222"]
    assert installed[0]["extension_params"]["project_namespace"] == "ns-bbbb2222"
