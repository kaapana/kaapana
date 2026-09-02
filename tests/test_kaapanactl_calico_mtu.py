import os
import re
import subprocess
from pathlib import Path

KAAPANACTL = Path(__file__).resolve().parents[1] / "kaapanactl.sh"


def test_set_calico_veth_mtu_pins_manifest_and_restarts_calico(tmp_path):
    # kaapanactl.sh runs main on load, so only the function under test is sourced.
    function = re.search(
        r"^function set_calico_veth_mtu \{.*?^\}", KAAPANACTL.read_text(), re.S | re.M
    )
    assert function, "set_calico_veth_mtu missing from kaapanactl.sh"
    cni_yaml = tmp_path / "cni.yaml"
    cni_yaml.write_text('  veth_mtu: "0"\n')
    calls = tmp_path / "kubectl.log"
    stub = tmp_path / "microk8s.kubectl"
    stub.write_text(f'#!/bin/bash\necho "$*" >> {calls}\n')
    stub.chmod(0o755)
    subprocess.run(
        ["bash", "-c", function.group(0) + f'\nset_calico_veth_mtu 1400 "{cni_yaml}"'],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        check=True,
        capture_output=True,
    )
    assert cni_yaml.read_text() == '  veth_mtu: "1400"\n'
    assert f"apply -f {cni_yaml}" in calls.read_text()
    assert "rollout restart ds/calico-node" in calls.read_text()
