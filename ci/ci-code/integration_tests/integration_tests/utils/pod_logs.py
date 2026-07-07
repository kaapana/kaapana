import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def fetch_failed_pod_logs(namespace: str, tail: int = 300) -> str:
    """
    SSH onto the deployment VM and return the logs of any Failed pod carrying
    the `kaapana.ai/type=processing-container` label in `namespace`.
    """
    vm_fqdn = os.environ.get("VM_FQDN")
    vm_user = os.environ.get("VM_USER")
    ssh_key = os.environ.get("ORCHESTRATOR_INSTANCE_PRIVATE_SSH_KEY")
    if not (vm_fqdn and vm_user and ssh_key):
        return "Could not fetch pod logs: VM_FQDN/VM_USER/ORCHESTRATOR_INSTANCE_PRIVATE_SSH_KEY not set."

    ssh_base = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{vm_user}@{vm_fqdn}",
    ]

    def run_remote(remote_cmd: str) -> tuple[int, str]:
        result = subprocess.run(
            ssh_base + [remote_cmd], capture_output=True, text=True, timeout=60
        )
        return result.returncode, (result.stdout + result.stderr).strip()

    rc, pod_names = run_remote(
        f"microk8s kubectl get pods -n {namespace} "
        "-l kaapana.ai/type=processing-container "
        "--field-selector=status.phase=Failed "
        "-o jsonpath='{.items[*].metadata.name}'"
    )
    if rc != 0:
        return f"Could not list failed pods in namespace {namespace}: {pod_names}"

    pod_names = pod_names.split()
    if not pod_names:
        return f"No Failed processing-container pods found in namespace {namespace}."

    logs = []
    for pod_name in pod_names:
        rc, output = run_remote(
            f"microk8s kubectl logs -n {namespace} {pod_name} --all-containers --tail={tail}"
        )
        logs.append(f"--- logs for pod {pod_name} (namespace {namespace}) ---\n{output}")
    return "\n\n".join(logs)
