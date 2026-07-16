import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def _run_remote(remote_cmd: str) -> tuple[int, str]:
    """
    Run a command on the deployment VM via SSH.
    Returns (-1, <reason>) if the SSH connection settings are not configured.
    """
    vm_fqdn = os.environ.get("VM_FQDN")
    vm_user = os.environ.get("VM_USER")
    ssh_key = os.environ.get("ORCHESTRATOR_INSTANCE_PRIVATE_SSH_KEY")
    if not (vm_fqdn and vm_user and ssh_key):
        return -1, "VM_FQDN/VM_USER/ORCHESTRATOR_INSTANCE_PRIVATE_SSH_KEY not set."

    ssh_base = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{vm_user}@{vm_fqdn}",
    ]
    result = subprocess.run(
        ssh_base + [remote_cmd], capture_output=True, text=True, timeout=60
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def fetch_airflow_task_logs(
    dag_id: str,
    run_id: str,
    tail: int = 300,
    services_namespace: str = "services",
) -> str:
    """
    Return the Airflow task logs of a dag run. Failed processing-container pods
    are deleted by KaapanaBaseOperator.on_failure, so the pod itself is usually
    gone by the time a test observes the failure — but its output was streamed
    into the Airflow task log, which persists in the af-logs PVC mounted in the
    scheduler pod.
    """
    log_dir = f"/kaapana/mounted/workflows/logs/dag_id={dag_id}/run_id={run_id}"
    rc, output = _run_remote(
        f"microk8s kubectl exec -n {services_namespace} deploy/airflow-scheduler -c scheduler -- "
        f"bash -c 'tail -n {tail} {log_dir}/task_id=*/attempt=*.log'"
    )
    if rc != 0:
        return f"Could not fetch airflow task logs for {dag_id=} {run_id=}: {output}"
    return f"--- airflow task logs for dag_id={dag_id} run_id={run_id} ---\n{output}"


def fetch_failed_pod_logs(namespace: str, tail: int = 300) -> str:
    """
    SSH onto the deployment VM and return the logs of any Failed pod carrying
    the `kaapana.ai/type=processing-container` label in `namespace`.
    """
    rc, pod_names = _run_remote(
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
        rc, output = _run_remote(
            f"microk8s kubectl logs -n {namespace} {pod_name} --all-containers --tail={tail}"
        )
        logs.append(f"--- logs for pod {pod_name} (namespace {namespace}) ---\n{output}")
    return "\n\n".join(logs)
