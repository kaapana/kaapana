import pytest
from task_api.processing_container import models
from pathlib import Path
import os
from task_api.runners.DockerRunner import DockerRunner
from task_api.processing_container import common

from conftest import LOCAL_REGISTRY, TASK_DIR, MODULE_PATH, k8s_cluster_available


def test_resources():
    from task_api.processing_container.resources import (
        human_readable_size,
        calculate_bytes,
        compute_memory_requirement,
    )

    sizes = [2342, 2346437, 87648, 1231, 0, 69234006234, 23423.4564]
    for size in sizes:
        assert abs(calculate_bytes(human_readable_size(size)) - size) <= int(size / 10)
    sr = models.ScaleRule(
        target_dir=".",
        target_glob="*.dcm",
        target_regex=".*",
        mode="sum",
        complexity="1*n**1",
        type="limit",
    )
    io = models.IOVolume(
        name="test-scale-rule",
        input=models.HostPathVolume(host_path=f"{TASK_DIR}/dummy/files"),
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


# def test_schemas_and_models(tmp_output_dir):
#     import filecmp

#     CURRENT_SCHEMA_PATH = f"{MODULE_PATH}/processing_container/schemas/"
#     NEW_MODEL_PATH = f"{tmp_output_dir}/generated_models/"
#     cmd = [
#         "datamodel-codegen",
#         "--input",
#         CURRENT_SCHEMA_PATH,
#         "--input-file-type",
#         "jsonschema",
#         "--output",
#         NEW_MODEL_PATH,
#         "--target-python-version",
#         "3.12",
#         "--output-model-type",
#         "pydantic_v2.BaseModel",
#         "--use-annotate",
#         "--disable-timestamp",
#         "--use-schema-description",
#     ]

#     subprocess.run(cmd, check=True)

#     CURRENT_MODEL_PATH = Path(f"{MODULE_PATH}/processing_container/generated_models/")

#     for model in CURRENT_MODEL_PATH.iterdir():
#         if model.name.endswith("schema.py"):
#             new_model = Path(NEW_MODEL_PATH, model.name)
#             assert filecmp.cmp(model, new_model)


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
