from task_api.processing_container.models import (
    ScaleRule,
    IOChannel,
    Mode,
    Resources,
    TaskInstance,
    Limits,
    Requests,
)
from pathlib import Path
from types import FunctionType
import re


def compute_target_size(io: IOChannel) -> int:
    """
    Compute the size of the input channel that should be used for scaling the resources
    """
    assert io.scale_rule
    scale_rule = io.scale_rule

    target_path = Path(io.input.host_path, scale_rule.target_dir)

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
    raise ValueError(
        f"Mode must be one of ['sum','max_file_size'] not {scale_rule.mode}"
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


def parse_complexity(complexity: str) -> FunctionType:
    """
    Return a function that calculates the memory requirements of the given complexity
    """
    pattern = re.compile(r"^[-+]?\d*(\.\d+)?\*?n(\*\*\d+)?$")
    assert pattern.match(complexity)

    coefficient = re.split(r"(?<!\*)\*(?!\*)", complexity)[0]
    exponent = complexity.split("**")[-1]

    def complexity(size: float) -> float:
        return int(coefficient) * size ** int(exponent)

    return complexity


def compute_memory_requirement(io: IOChannel) -> int:
    """
    Compute the memory requirements for the inpute channel based on the files in the local file path.
    """

    target_size = compute_target_size(io=io)
    complexity = parse_complexity(io.scale_rule.complexity)
    print(f"{target_size=}")

    return complexity(target_size)


def compute_memory_resources(task_instance: TaskInstance) -> Resources:
    """
    Return a Resources object based on the Resources and ScaleRule in the task_instance object.

    Compute the memory requirement of each input channel based on given ScaleRules.

    The final memory requests and limits correspond the maximum of the given Resource limit
    and the memory requirement computed from the ScaleRule.
    """
    if task_instance.resources:
        task_resources = task_instance.resources
    else:
        task_resources = Resources(limits=Limits(), requests=Requests())
    memory_request = (
        calculate_bytes(task_resources.requests.memory)
        if task_resources.requests.memory
        else 0
    )
    memory_limit = (
        calculate_bytes(task_resources.limits.memory)
        if task_resources.limits.memory
        else 0
    )
    for channel in task_instance.inputs:
        if rule := channel.scale_rule:
            if rule.type == "limit":
                memory_limit = max(memory_limit, compute_memory_requirement(channel))
            elif rule.type == "request":
                memory_request = max(
                    memory_request, compute_memory_requirement(channel)
                )

    if memory_limit >= 10:
        task_resources.limits.memory = human_readable_size(1.1 * memory_limit)
    if memory_request >= 10:
        task_resources.requests.memory = human_readable_size(1.1 * memory_request)

    return task_resources
