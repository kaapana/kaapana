"""Regression test for the CRD guard in kaapanactl.sh: a chart CRD that already exists but is
terminating must stop the deploy before Helm silently skips it and the install fails with
"no matches for kind ...". Runs the guard function with a stubbed helm and kubectl on PATH."""

import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "kaapanactl.sh"


def test_terminating_crd_stops_deploy(tmp_path):
    guard = re.search(r"^function wait_for_chart_crds .*?^}", SCRIPT.read_text(), re.M | re.S)
    assert guard, "wait_for_chart_crds missing from kaapanactl.sh"
    (tmp_path / "helm").write_text(
        "#!/bin/sh\nprintf 'kind: CustomResourceDefinition\\nmetadata:\\n  name: ingressroutes.traefik.io\\n'\n"
    )
    (tmp_path / "microk8s.kubectl").write_text("#!/bin/sh\necho 2026-01-01T00:00:00Z\n")
    for stub in ("helm", "microk8s.kubectl"):
        (tmp_path / stub).chmod(0o755)
    result = subprocess.run(
        ["bash", "-c", f"set -euf -o pipefail; RED=; NC=; HELM_EXECUTABLE=helm; CHART_PATH=x.tgz\n{guard.group(0)}\nwait_for_chart_crds"],
        env={"PATH": f"{tmp_path}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "ingressroutes.traefik.io" in result.stdout and "finalizers" in result.stdout
