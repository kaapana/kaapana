import pytest
from task_api.processing_container import task_models
from task_api.processing_container import pc_models
from pathlib import Path
import os
from task_api.runners.DockerRunner import DockerRunner
from task_api.processing_container import common
import re

from conftest import LOCAL_REGISTRY, TASK_DIR, MODULE_PATH, k8s_cluster_available


def is_valid_pod_name(name: str) -> bool:
    pod_name_regex = re.compile(
        r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$"
    )
    """Check if a string is a valid Kubernetes pod name."""
    if not isinstance(name, str):
        return False
    if len(name) > 63:
        return False
    return pod_name_regex.match(name) is not None


@pytest.mark.skipif(
    condition=not (
        k8s_cluster_available()
        and os.getenv("REGISTRY_URL")
        and os.getenv("REGISTRY_USER")
        and os.getenv("REGISTRY_PASSWORD")
    ),
    reason="Kubernetes cluster not available",
)
@pytest.mark.parametrize(
    "input_name",
    [
        "validname",
        "valid-name-123",
        "evaluate-segmentations-250922070517319578-put-eval-metrics-to-",
        "a" * 63,
    ],
)
def test_pod_name(input_name):
    from task_api.runners.KubernetesRunner import generate_pod_name

    pod_name = generate_pod_name(input_name)
    assert is_valid_pod_name(pod_name), f"Invalid pod name: {pod_name}"


@pytest.mark.parametrize(
    "bad_name",
    [
        "InvalidUpper",
        "-startswithdash",
        "endswithdash-",
        "contains_underscore",
        "a" * 64,
    ],
)
def test_invalid_examples(bad_name):
    assert not is_valid_pod_name(bad_name)


def test_merge_env():
    pc_env = [
        pc_models.TaskTemplateEnv(name="VAR1", value="0"),
        pc_models.TaskTemplateEnv(name="VAR2", value="0"),
    ]
    task_env = [
        pc_models.BaseEnv(name="VAR1", value="1"),
        pc_models.BaseEnv(name="VAR3", value="1"),
    ]
    expected_name_value_pairs = {"VAR1": "1", "VAR2": "0", "VAR3": "1"}
    merged_env = common.merge_env(pc_env, task_env)
    for env in merged_env:
        for name, value in expected_name_value_pairs.items():
            if env.name == name:
                assert (env.name, env.value) == (name, value)


def test_resources():
    from task_api.processing_container.resources import (
        human_readable_size,
        calculate_bytes,
        compute_memory_requirement,
    )

    sizes = [2342, 2346437, 87648, 1231, 0, 69234006234, 23423.4564]
    for size in sizes:
        assert abs(calculate_bytes(human_readable_size(size)) - size) <= int(size / 10)
    sr = pc_models.ScaleRule(
        target_dir=".",
        target_glob="*.dcm",
        target_regex=".*",
        mode="sum",
        complexity="1*n**1",
        type="limit",
    )
    io = task_models.IOVolume(
        name="test-scale-rule",
        input=task_models.HostPathVolume(host_path=f"{TASK_DIR}/dummy/files"),
        scale_rule=sr,
    )
    compute_memory_requirement(io=io)


def test_task_template():
    task_template = common.get_task_template(
        image=f"{LOCAL_REGISTRY}/dummy:latest",
        task_identifier="upstream",
        mode="docker",
    )
    os.environ["registryUrl"] = str(LOCAL_REGISTRY)

    task = common.parse_task(
        file=f"{TASK_DIR}/dummy/tasks/upstream-task.json",
    )
    task_instance = common.create_task_instance(task_template, task)


def test_docker_runner(tmp_output_dir):
    os.environ["registryUrl"] = str(LOCAL_REGISTRY)
    os.environ["output_dir"] = str(tmp_output_dir)

    task = common.parse_task(file=f"{TASK_DIR}/dummy/tasks/upstream-task.json")
    task_run = DockerRunner.run(task=task)
    DockerRunner.logs(task_run, follow=True)
    DockerRunner.check_status(task_run=task_run, follow=True)
    output = tmp_output_dir / "task_test_docker_runner"
    DockerRunner.dump(task_run, output=output)

    assert Path(tmp_output_dir, "dummy/channel1/dummy.txt").exists()
    assert Path(tmp_output_dir, "dummy/channel2/dummy.txt").exists()
    assert Path(output).exists()

    task = common.parse_task(file=f"{TASK_DIR}/dummy/tasks/downstream-task.json")
    task_run = DockerRunner.run(task=task)
    DockerRunner.monitor_memory(task_run)


@pytest.mark.skipif(
    condition=not (
        k8s_cluster_available()
        and os.getenv("REGISTRY_URL")
        and os.getenv("REGISTRY_USER")
        and os.getenv("REGISTRY_PASSWORD")
    ),
    reason="Kubernetes cluster not available",
)
@pytest.mark.usefixtures("push_to_registry")
def test_kubernetes_runner(tmp_output_dir):
    from task_api.runners.KubernetesRunner import KubernetesRunner

    os.environ["output_dir"] = str(tmp_output_dir)
    os.environ["registryUrl"] = os.getenv("REGISTRY_URL")
    os.environ["registryUsername"] = os.getenv("REGISTRY_USER")
    os.environ["registryPassword"] = os.getenv("REGISTRY_PASSWORD")
    os.environ["namespace"] = "default"
    task = common.parse_task(
        file=f"{TASK_DIR}/dummy/tasks/upstream-task.json",
    )
    KubernetesRunner.run(task)


def test_cli_run(tmp_output_dir):
    from task_api import cli

    os.environ["registryUrl"] = str(LOCAL_REGISTRY)
    os.environ["output_dir"] = str(tmp_output_dir)

    output = tmp_output_dir / "task_test_cli_run_upstream.json"
    cli.run(
        input=Path(f"{TASK_DIR}/dummy/tasks/upstream-task.json"),
        mode=cli.Modes.docker,
        watch=True,
        output=output,
        monitor_memory=False,
    )
    cli.logs(output)
    cli.check_task_run(output)

    assert Path(tmp_output_dir, "dummy/channel1/dummy.txt").exists()
    assert Path(tmp_output_dir, "dummy/channel2/dummy.txt").exists()
    assert Path(output).exists()

    output = tmp_output_dir / "task_test_cli_run_downstream.json"
    cli.run(
        input=Path(f"{TASK_DIR}/dummy/tasks/downstream-task.json"),
        mode=cli.Modes.docker,
        monitor_memory=True,
        watch=False,
        output=output,
    )

    assert Path(output).exists()


def test_cli_processing_container(tmp_output_dir):
    from task_api import cli

    cli.processing_container(
        image=f"{LOCAL_REGISTRY}/dummy:latest", mode=cli.Modes.docker
    )
