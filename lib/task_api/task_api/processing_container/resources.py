from task_api.processing_container import task_models
from task_api.processing_container import pc_models
from kubernetes import client as k8sclient
from pathlib import Path
from typing import Optional
import json
import os
import re
import urllib.error
import urllib.request

PROJECT_RUNTIME_TIMEOUT = int(os.getenv("PROJECT_RUNTIME_TIMEOUT", "30"))


def compute_target_size(
    io: task_models.IOChannel,
    namespace: Optional[str] = None,
) -> int:
    """
    Compute the size of the input channel that should be used for scaling the resources
    """
    assert io.scale_rule
    scale_rule = io.scale_rule
    if isinstance(io.volume_source, k8sclient.V1Volume) and io.volume_source.persistent_volume_claim:
        return compute_pvc_target_size(io=io, namespace=namespace)

    local_path = getattr(io.volume_source, "host_path", None)
    if not local_path:
        raise ValueError(
            f"Cannot compute scale_rule for unsupported volume source {type(io.volume_source)}"
        )

    target_path = Path(local_path, scale_rule.target_dir)

    if scale_rule.mode.value == "sum":
        return sum_of_file_sizes(
            target_path=target_path,
            target_glob=scale_rule.target_glob,
            target_regex=scale_rule.target_regex,
        )
    elif scale_rule.mode.value == "max_file_size":
        return max_file_size(
            target_path=target_path,
            target_glob=scale_rule.target_glob,
            target_regex=scale_rule.target_regex,
        )
    elif scale_rule.mode.value == "max_item_sum":
        item_paths = [p for p in Path(local_path).glob("*") if p.is_dir()]
        return max(
            [
                sum_of_file_sizes(
                    target_path=Path(item_path, scale_rule.target_dir),
                    target_glob=scale_rule.target_glob,
                    target_regex=scale_rule.target_regex,
                )
                for item_path in item_paths
            ]
        )

    raise ValueError(
        f"Mode must be one of ['sum','max_file_size','max_item_sum'] not {scale_rule.mode}"
    )


def sum_of_file_sizes(
    target_path: Path, target_glob: str = "*", target_regex: str = ".*"
):
    target_size = 0
    pattern = re.compile(target_regex)
    for file_path in target_path.rglob(target_glob):
        if file_path.is_file() and pattern.fullmatch(
            str(file_path.relative_to(target_path))
        ):
            target_size += file_path.stat().st_size
    return target_size


def max_file_size(target_path: Path, target_glob: str = "*", target_regex: str = ".*"):
    target_size = 0
    pattern = re.compile(target_regex)
    for file_path in target_path.rglob(target_glob):
        if file_path.is_file() and pattern.fullmatch(
            str(file_path.relative_to(target_path))
        ):
            target_size = max(file_path.stat().st_size, target_size)
    return target_size


def human_readable_size(size: int, suffix=""):
    """
    Return human readable size
    """
    for unit in ("B", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(size) < 1024.0:
            return f"{size:3.1f}{unit}{suffix}"
        size /= 1024.0
    return f"{size:.1f}Yi{suffix}"


def calculate_bytes(size: str) -> int:
    """
    Return the number of bytes from a human readable size string
    """

    units = ("B", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi")
    exponent_by_size = {unit: i for i, unit in enumerate(units)}

    match = re.match(r"^(-?\d+(?:\.\d+)?)([a-zA-Z]+)$", size)
    if not match:
        raise ValueError(f"Invalid format: {size}")

    size, unit = float(match.group(1)), match.group(2)

    return size * 1024.0 ** exponent_by_size.get(unit)


def compute_memory_requirement(
    io: task_models.IOChannel,
    namespace: Optional[str] = None,
) -> int:
    """
    Compute the memory requirements for the inpute channel based on the files in the local file path.
    """

    target_size = compute_target_size(io=io, namespace=namespace)

    return io.scale_rule.scale_factor * target_size


def compute_pvc_target_size(
    io: task_models.IOChannel,
    namespace: str,
) -> int:

    scale_rule = io.scale_rule
    payload = {
        "claim_name": io.volume_source.persistent_volume_claim.claim_name,
        "sub_path": io.sub_path,
        "scale_rule": {
            "mode": scale_rule.mode.value,
            "target_dir": scale_rule.target_dir,
            "target_regex": scale_rule.target_regex,
            "target_glob": scale_rule.target_glob,
        },
    }
    url = f"http://project-runtime-service.{namespace}.svc:8080/filesystem/measure"
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=PROJECT_RUNTIME_TIMEOUT
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Failed to resolve PVC scale_rule through project-runtime in namespace {namespace}: {e}"
        ) from e
    return data["target_size"]


def compute_memory_resources(
    task_instance: task_models.TaskInstance,
) -> pc_models.Resources:
    """
    Return a Resources object based on the Resources and ScaleRule in the task_instance object.

    Compute the memory requirement of each input channel based on given ScaleRules.

    The final memory requests and limits correspond the maximum of the given Resource limit
    and the memory requirement computed from the ScaleRule.
    """
    if task_instance.resources:
        task_resources = task_instance.resources
    else:
        task_resources = pc_models.Resources(limits={}, requests={})
    memory_request = (
        calculate_bytes(task_resources.requests.get("memory"))
        if task_resources.requests.get("memory")
        else 0
    )
    memory_limit = (
        calculate_bytes(task_resources.limits.get("memory"))
        if task_resources.limits.get("memory")
        else 0
    )
    for channel in task_instance.inputs:
        if rule := channel.scale_rule:
            if rule.type == "limit":
                memory_limit = max(
                    memory_limit,
                    compute_memory_requirement(channel, namespace=task_instance.config.namespace),
                )
            elif rule.type == "request":
                memory_request = max(
                    memory_request,
                    compute_memory_requirement(channel, namespace=task_instance.config.namespace),
                )

    if memory_limit >= 10:
        task_resources.limits["memory"] = human_readable_size(1.1 * memory_limit)
    if memory_request >= 10:
        task_resources.requests["memory"] = human_readable_size(1.1 * memory_request)

    return task_resources
