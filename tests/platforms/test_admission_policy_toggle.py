import shutil
import subprocess
from pathlib import Path

import pytest

CHART = Path(__file__).resolve().parents[2] / "platforms/kaapana-admin-chart"


def render_admission_policy(tmp_path, *set_args):
    # kaapana-admin-chart lists 14 dependencies helm would insist on, so render the one
    # template inside a throwaway chart holding only it and the real values.yaml.
    chart = tmp_path / "chart"
    (chart / "templates").mkdir(parents=True, exist_ok=True)
    (chart / "Chart.yaml").write_text("apiVersion: v2\nname: probe\nversion: 0.0.0\n")
    shutil.copy(CHART / "values.yaml", chart / "values.yaml")
    shutil.copy(CHART / "templates/validation_admission_policy.yaml", chart / "templates")
    cmd = ["helm", "template", str(chart)]
    for arg in set_args:
        cmd += ["--set", arg]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


@pytest.mark.skipif(shutil.which("helm") is None, reason="needs the helm binary")
def test_privileged_pod_policy_can_be_disabled_without_dev_mode(tmp_path):
    # Enforced by default; a site must be able to switch it off without dev_mode (#2301).
    assert "ValidatingAdmissionPolicy" in render_admission_policy(tmp_path)
    assert "ValidatingAdmissionPolicy" not in render_admission_policy(
        tmp_path, "global.enable_privileged_pod_admission_policy=false"
    )
