import json
import logging
from dotenv import load_dotenv
from task_api.processing_container.models import Task, TaskRun, IOChannel, ScaleRule
from task_api.processing_container.common import (
    get_processing_container,
    parse_task,
    parse_processing_container,
)
from task_api.runners.DockerRunner import DockerRunner
from task_api.runners.KubernetesRunner import KubernetesRunner
from task_api.processing_container.resources import (
    sum_of_file_sizes,
    max_file_size,
    human_readable_size,
    compute_target_size,
    compute_memory_requirement,
    calculate_bytes,
)


from typing import Optional
from pathlib import Path
import typer
from enum import Enum
import sys

app = typer.Typer(help="Kaapana Task Runner CLI")
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("task-runner")


class Modes(str, Enum):
    docker = "docker"
    kubernetes = "k8s"


class Schema(str, Enum):
    task = "task"
    processing_container = "pc"


def monitor_container_memory(task_run: TaskRun):
    max_memory_usage = human_readable_size(DockerRunner.monitor_memory(task_run))
    typer.echo(f"Peak memory usage of container: {max_memory_usage}")

    for channel in task_run.inputs:
        sum_input_size = human_readable_size(
            sum_of_file_sizes(target_path=Path(channel.input.local_path))
        )
        max_input_size = human_readable_size(
            max_file_size(target_path=Path(channel.input.local_path))
        )

        typer.echo(f"Sum of all files for {channel}: {sum_input_size}")
        typer.echo(f"Size of largest file for {channel} {max_input_size}")

        if channel.scale_rule:
            size_scale_rule_target = human_readable_size(
                compute_target_size(io=channel)
            )
            typer.echo(
                f"Size of target of ScaleRule for {channel}: {size_scale_rule_target}"
            )
            scaleRule_outcome = human_readable_size(compute_memory_requirement(channel))
            typer.echo(
                f"Resource {channel.scale_rule.type} from scaleRule: {scaleRule_outcome}"
            )

            if calculate_bytes(scaleRule_outcome) <= calculate_bytes(max_memory_usage):
                msg = "\u274c Resource {}: {} is smaller than the peak memory usage {}"
                typer.echo(
                    msg.format(
                        channel.scale_rule.type, scaleRule_outcome, max_memory_usage
                    )
                )


@app.command()
def processing_container(
    image: str = typer.Argument(
        ..., help="Image to get the processing-container.json for"
    ),
    mode: Optional[Modes] = typer.Option(
        Modes.docker.value,
        help="Environemnt in which to run the container.",
    ),
):
    """
    Return the processing-container json for the image
    """
    processing_container_json = get_processing_container(image, mode=mode.value)
    typer.echo(processing_container_json.model_dump_json(indent=2))


@app.command()
def check_task_run(
    task_run: Path = typer.Argument(
        ..., help="task_run.json file to run a container for."
    ),
    watch: bool = typer.Option(True, help="Wether to check the state until finished."),
):
    """ """
    with open(task_run, "r") as f:
        task_data = TaskRun(**json.load(f))

    if task_data.mode == "docker":
        DockerRunner.check_status(task_data, follow=watch)
    else:
        typer.echo("Only supported for tasks run in docker mode.")


@app.command()
def run(
    input: Path = typer.Argument(
        ..., help="Path to task.json file to run a container for."
    ),
    mode: Optional[Modes] = typer.Option(
        Modes.docker.value,
        help="Environemnt in which to run the container. One of ['docker', 'kubernetes'].",
    ),
    watch: Optional[bool] = typer.Option(False, help="Stream logs to stdout."),
    output: Optional[Path] = typer.Option(
        None, help="Path to dump the task_run object."
    ),
    monitor_memory: bool = typer.Option(
        False,
        help="Monitor memory utilization of the processing-container in Docker. Does not work in conjunction with watch!",
    ),
):
    """
    Start a container for a given task.json file
    """

    if mode.value == Modes.docker.value:
        runner = DockerRunner

    elif mode.value == Modes.kubernetes.value:
        runner = KubernetesRunner
    task = parse_task(input)
    task_run = runner.run(task)
    runner.dump(task_run, output=output)

    typer.echo(f"{task_run.model_dump(mode="json")}")
    if watch:
        runner.logs(task_run, follow=watch)

    if monitor_memory and (not watch) and mode.value == Modes.docker.value:
        monitor_container_memory(task_run)


@app.command()
def logs(
    task: Path = typer.Argument(..., help="Path to task_run.json"),
    watch: Optional[bool] = typer.Option(False, help="Stream logs to stdout."),
):
    """Get logs from a task"""
    with open(task, "r") as f:
        task_run = TaskRun(**json.load(f))
    if task_run.mode == "docker":
        runner = DockerRunner
    elif task_run.mode == "k8s":
        runner = KubernetesRunner
    runner.logs(task_run, watch)


@app.command()
def validate(
    input: Path = typer.Argument(..., help="Path to the file to validate"),
    schema: Schema = typer.Option(
        default=Schema.task.value,
    ),
):
    """
    Validate a task or processing-container configuration file.
    """
    if schema.value == schema.task:
        try:
            parse_task(input)
        except ValueError as e:
            typer.echo(f"\u274c {input} is not a valid task!")
            typer.echo(e)
            sys.exit(1)
        except FileNotFoundError:
            typer.echo(f"\u274c {input} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            typer.echo(f"\u274c {input} is not valid json!")
            typer.echo(e)
            sys.exit(1)
        typer.echo("\u2705 valid task")
    elif schema.value == schema.processing_container:
        try:
            parse_processing_container(input)
        except ValueError as e:
            typer.echo(f"\u274c {input} is not a valid processing_container.json file!")
            typer.echo(e)
            sys.exit(1)
        except FileNotFoundError:
            typer.echo(f"\u274c {input} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            typer.echo(f"\u274c {input} is not valid json!")
            typer.echo(e)
            sys.exit(1)
        typer.echo("\u2705 valid processing_container.json file")


if __name__ == "__main__":
    app()
