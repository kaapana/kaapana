# Runs scripts/preinstall_extensions.py with its helm/kube boundary stubbed out,
# so the bookkeeping of the post-install status loop can be checked offline.
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "preinstall_extensions.py"


def test_status_loop_keeps_each_release_version(tmp_path, monkeypatch):
    # Two preinstalled extensions with different versions: the status loop must
    # not overwrite one release's version with the other's (#2300).
    extensions = [{"name": "a", "version": "1.0"}, {"name": "b", "version": "2.0"}]
    for ext in extensions:
        (tmp_path / f'{ext["name"]}-{ext["version"]}.tgz').touch()
    monkeypatch.setenv("PREINSTALL_EXTENSIONS", json.dumps(extensions))
    monkeypatch.setattr("time.sleep", lambda _: None)
    settings = SimpleNamespace(helm_extensions_cache=str(tmp_path), helm_namespace="ns")
    kube_ok = (True, None, None, {"status": ["running"], "name": ["pod"]})
    stubs = {
        "app": SimpleNamespace(),
        "app.config": SimpleNamespace(settings=settings),
        "app.helm_helper": SimpleNamespace(
            helm_show_chart=lambda *a: {}, get_kube_objects=lambda *a, **k: kube_ok
        ),
        "app.utils": SimpleNamespace(
            helm_status=lambda *a, **k: {},
            supervised_helm_install=lambda ext, **k: (
                True, "", None, ext["name"], None
            ),
        ),
        "kaapanapy": SimpleNamespace(),
        "kaapanapy.logger": SimpleNamespace(get_logger=lambda _: mock.Mock()),
    }
    with mock.patch.dict(sys.modules, stubs):
        result = runpy.run_path(str(SCRIPT))
    recorded = {r: v["version"] for r, v in result["releases_installed"].items()}
    assert recorded == {"a": "1.0", "b": "2.0"}
