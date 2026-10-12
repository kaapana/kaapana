"""Regression tests for check_chart_crds in kaapanactl.sh: a chart CRD that already exists but
is being deleted or not served must stop the deploy before Helm skips it and the install fails
with "no matches for kind ...". Runs the function once against a stubbed helm and kubectl.
"""

import re
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "kaapanactl.sh"

# Both stubs act on $CRD_STATE. helm lists two CRDs, but only for the chart.tgz passed in.
HELM = """#!/bin/sh
[ "$3" = chart.tgz ] && [ "$CRD_STATE" != unreadable-chart ] \\
    || { echo "Error: path \\"$3\\" not found" >&2; exit 1; }
printf 'kind: CustomResourceDefinition\\nmetadata:\\n  name: %s\\n---\\n' \\
    ingressroutes.traefik.io middlewares.traefik.io
"""
KUBECTL = """#!/bin/sh
[ "$CRD_STATE" = unreachable ] && { echo 'connection to the server was refused' >&2; exit 1; }
case "$*" in
    *--ignore-not-found*) [ "$CRD_STATE" = absent ] || echo "crd/$3" ;;
    *deletionTimestamp*) [ "$CRD_STATE" = deleting ] && echo 2026-01-01T00:00:00Z ;;
    "get crd"*) ;;
    *) [ "$CRD_STATE" = unserved ] && { echo "no resource type $2" >&2; exit 1; } ;;
esac
exit 0
"""

CASES = {  # $CRD_STATE: (exit code, expected in output)
    "absent": (0, ""),  # fresh install: Helm creates the CRDs itself
    "served": (0, ""),  # redeploy: Helm never removes crds/
    "deleting": (1, "CRD middlewares.traefik.io is being deleted"),  # all reported
    "unserved": (1, "exists but is not served"),  # fails at once, never waits
    "unreachable": (1, "connection to the server was refused"),  # not "absent"
    "unreadable-chart": (1, 'path "chart.tgz" not found'),  # not "no CRDs"
}


@pytest.mark.parametrize("crd_state", CASES)
def test_check_chart_crds(tmp_path, crd_state):
    function = re.search(
        r"^function check_chart_crds .*?^}", SCRIPT.read_text(), re.M | re.S
    )
    assert function, "check_chart_crds missing from kaapanactl.sh"
    for name, stub in (("helm", HELM), ("kubectl", KUBECTL)):
        (tmp_path / name).write_text(stub)
        (tmp_path / name).chmod(0o755)
    setup = "set -euf -o pipefail; RED=; NC=; HELM_EXECUTABLE=helm; KUBECTL_EXECUTABLE=kubectl"
    result = subprocess.run(
        ["bash", "-c", f"{setup}\n{function.group(0)}\ncheck_chart_crds chart.tgz"],
        env={"PATH": f"{tmp_path}:/usr/bin:/bin", "CRD_STATE": crd_state},
        capture_output=True,
        text=True,
        timeout=10,  # raises TimeoutExpired if the check waits instead of looking once
    )
    output = result.stdout + result.stderr
    exit_code, expected = CASES[crd_state]
    assert result.returncode == exit_code, output
    assert expected in output
