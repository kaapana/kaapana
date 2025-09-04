import pytest
from task_api.processing_container import models
from pathlib import Path
import subprocess
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
        input=models.LocalPath(
            local_path=f"{TASK_DIR}/mask2nifti/test-data/workflow_dir"
        ),
        scale_rule=sr,
    )
    compute_memory_requirement(io=io)


def test_task_template():
    task_template = common.get_task_template(
        image=f"{LOCAL_REGISTRY}/dummy:latest", task_identifier="default", mode="docker"
    )
    task = common.parse_task(
        file=f"{TASK_DIR}/dummy/tasks/test_task.json",
        custom_vars={"registry": LOCAL_REGISTRY, "task_dir": TASK_DIR},
    )
    task_instance = common.create_task_instance(task_template, task)


def test_docker_runner(tmp_output_dir):
    task = common.parse_task(
        file=f"{TASK_DIR}/dummy/tasks/test_task.json",
        custom_vars={"registry": LOCAL_REGISTRY, "output_dir": tmp_output_dir},
    )
    task_run = DockerRunner.run(task=task)
    DockerRunner.logs(task_run, follow=True)
    DockerRunner.check_status(task_run=task_run, follow=True)
    output = tmp_output_dir / "task_run-test-custom-vars"
    DockerRunner.dump(task_run, output=output)

    assert Path(tmp_output_dir, "dummy/channel1/dummy.txt").exists()
    assert Path(tmp_output_dir, "dummy/channel2/dummy.txt").exists()
    assert Path(output).exists()

    os.environ["registry"] = str(LOCAL_REGISTRY)
    os.environ["output_dir"] = str(tmp_output_dir)
    task = common.parse_task(
        file=f"{TASK_DIR}/downstream/tasks/test_downstream_with_env.json"
    )
    task_run = DockerRunner.run(task=task)
    DockerRunner.monitor_memory(task_run)


@pytest.mark.skipif(
    condition=not k8s_cluster_available(), reason="Kubernetes cluster not available"
)
def test_kubernetes_runner(tmp_output_dir):
    from task_api.runners.KubernetesRunner import KubernetesRunner

    task = common.parse_task(
        file=f"{TASK_DIR}/dummy/tasks/test_task.json",
        custom_vars={"registry": LOCAL_REGISTRY, "output_dir": tmp_output_dir},
    )
    KubernetesRunner.run(task, dry_run=True)


def test_schemas_and_models(tmp_output_dir):
    import filecmp

    CURRENT_SCHEMA_PATH = f"{MODULE_PATH}/processing_container/schemas/"
    NEW_MODEL_PATH = f"{tmp_output_dir}/generated_models/"
    cmd = [
        "datamodel-codegen",
        "--input",
        CURRENT_SCHEMA_PATH,
        "--input-file-type",
        "jsonschema",
        "--output",
        NEW_MODEL_PATH,
        "--target-python-version",
        "3.12",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--use-annotate",
        "--disable-timestamp",
        "--use-schema-description",
    ]

    subprocess.run(cmd, check=True)

    CURRENT_MODEL_PATH = Path(f"{MODULE_PATH}/processing_container/generated_models/")

    for model in CURRENT_MODEL_PATH.iterdir():
        if model.name.endswith("schema.py"):
            new_model = Path(NEW_MODEL_PATH, model.name)
            assert filecmp.cmp(model, new_model)


def test_cli_run(tmp_output_dir):
    from task_api import cli

    os.environ["registry"] = str(LOCAL_REGISTRY)
    os.environ["output_dir"] = str(tmp_output_dir)

    output = tmp_output_dir / "task_run-cli-test-env.json"
    cli.run(
        input=Path(f"{TASK_DIR}/dummy/tasks/test_env_task.json"),
        mode=cli.Modes.docker,
        watch=True,
        output=output,
        monitor_memory=False,
    )
    cli.logs(output)
    cli.check_task_run(output)

    assert Path(tmp_output_dir, "env/channel1/dummy.txt").exists()
    assert Path(tmp_output_dir, "env/channel2/dummy.txt").exists()
    assert Path(output).exists()

    output = tmp_output_dir / "task_run-test-cli-downstream.json"
    cli.run(
        input=Path(f"{TASK_DIR}/downstream/tasks/test_downstream_with_env.json"),
        mode=cli.Modes.docker,
        monitor_memory=True,
        watch=False,
        output=output,
    )

    assert Path(output).exists()


def test_cli_processing_container(tmp_output_dir):
    from task_api import cli

    os.environ["registry"] = str(LOCAL_REGISTRY)
    os.environ["output_dir"] = str(tmp_output_dir)
    cli.processing_container(
        image=f"{LOCAL_REGISTRY}/dummy:latest", mode=cli.Modes.docker
    )
