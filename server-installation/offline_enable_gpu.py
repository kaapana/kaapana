#!/usr/bin/env python3

import json
import pathlib
import subprocess

chart_name = "gpu-operator"
chart_version = "v22.9.2"
chart_path = "/home/kaapana/installation-scipts/gpu-operator.tgz"

try:
    subprocess.check_call(["nvidia-smi", "-L"])
    driver = "host"
except OSError:
    driver = "operator"

CONTAINERD_SOCKET = pathlib.Path("/var/snap/microk8s/common/run/containerd.sock")
CONTAINERD_TOML = pathlib.Path(
    "/var/snap/microk8s/current/args/containerd-template.toml"
)

helm_args = [
    "install",
    chart_name,
    chart_path,
    f"--version={chart_version}",
    "--create-namespace",
    f"--namespace={chart_name}-resources",
    "-f",
    "-",
]

helm_config = {
    "operator": {
        "defaultRuntime": "containerd",
    },
    "driver": {
        "enabled": ("true" if driver == "operator" else "false"),
    },
    "toolkit": {
        "enabled": "true",
        "env": [
            {"name": "CONTAINERD_CONFIG", "value": CONTAINERD_TOML.as_posix()},
            {"name": "CONTAINERD_SOCKET", "value": CONTAINERD_SOCKET.as_posix()},
            {
                "name": "CONTAINERD_SET_AS_DEFAULT",
                "value": "1",
            },
        ],
    },
}


HELM = "/snap/bin/helm"
subprocess.run([HELM, *helm_args], input=json.dumps(helm_config).encode())
