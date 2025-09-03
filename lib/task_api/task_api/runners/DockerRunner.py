import subprocess
from pathlib import Path
import docker
import sys, os
import time

from task_api.processing_container.models import (
    TaskRun,
    Task,
    Resources,
    TaskInstance,
)
from task_api.processing_container.resources import (
    calculate_bytes,
    compute_memory_requirement,
    human_readable_size,
)
from task_api.processing_container.common import (
    get_processing_container,
    create_task_instance,
)

from task_api.runners.base import BaseRunner


class DockerRunner(BaseRunner):
    client = docker.from_env()

    @classmethod
    def run(cls, task: Task, dry_run: bool = False):
        cls._logger.info("Running task in Docker...")

        processing_container = get_processing_container(
            task.image, task.taskTemplate, mode="docker"
        )
        task_instance = create_task_instance(
            processing_container=processing_container, task=task
        )

        cls._logger.info(f"TaskInstance: {task_instance.model_dump()}")
        memory_limit = int(cls._set_memory_limit(task_instance=task_instance))
        if memory_limit >= 10:
            task.resources.limits.memory = human_readable_size(memory_limit)
        else:
            memory_limit = None

        input_volumes = {
            vol.input.local_path: {"bind": vol.mounted_path, "mode": "ro"}
            for vol in task_instance.inputs
        }
        output_volumes = {
            vol.input.local_path: {"bind": vol.mounted_path, "mode": "rw"}
            for vol in task_instance.outputs
            if vol.input.local_path not in input_volumes
        }

        if dry_run:
            id = "dummy-id"
        else:
            container = cls.client.containers.run(
                image=task_instance.image,
                command=task_instance.command,
                labels={"kaapana.type": "processing-container"},
                environment={env.name: env.value for env in task_instance.env},
                detach=True,
                volumes={**input_volumes, **output_volumes},
                mem_limit=memory_limit,
            )

            id = container.id

        return TaskRun(id=id, mode="docker", **task_instance.model_dump())

    @classmethod
    def logs(cls, task_run: TaskRun, follow: bool = False):
        if follow:
            cls._logger.info("Start log streaming")
        container = cls.client.containers.get(container_id=task_run.id)
        logs = container.logs(stream=follow)
        try:
            for line in logs:
                cls._logger.info(line.decode().rstrip())
            for line in logs:
                cls._logger.error(line.decode().rstrip())
        except KeyboardInterrupt:
            cls._logger.error("Log streaming interrupted.")
        finally:
            logs.close()

    @classmethod
    def stop(cls, task_run: TaskRun):
        raise NotImplementedError()

    @classmethod
    def _set_memory_limit(cls, task_instance: TaskInstance) -> int:
        """
        Return the memory limit for a task_instance based on Resources and ScaleRules
        """
        memory_limit = 0
        if (
            task_instance.resources
            and task_instance.resources.limits
            and task_instance.resources.limits.memory
        ):
            memory_limit = calculate_bytes(task_instance.resources.limits.memory)

        for channel in task_instance.inputs:
            if channel.scale_rule and channel.scale_rule.type.value == "limit":
                scale_rule_memory_limit = compute_memory_requirement(channel)
                memory_limit = max(memory_limit, scale_rule_memory_limit)
        return memory_limit

    @classmethod
    def check_status(cls, task_run: TaskRun, follow: bool = False):
        container_id = task_run.id
        container = cls.client.containers.get(container_id=container_id)

        running = True
        while running and follow:
            state = container.attrs.get("State")
            if state.get("OOMKilled"):
                cls._logger.error("Container stopped because of OutOfMemory!")
                sys.exit(137)

            if state.get("Status") == "exited" and state.get("ExitCode") != 0:
                exit_code = state.get("ExitCode")
                cls._logger.error(f"Container returned exit code {exit_code}")
                sys.exit(exit_code)

            if state.get("Status") == "exited" and state.get("ExitCode") == 0:
                cls._logger.info("Container exited with status code 0")
                return

            running = state.get("Running")

    @classmethod
    def monitor_memory(cls, task_run: TaskRun):
        """
        Monitor the memory usage of a container and return the maxmimum memory utilization.
        """
        cls._logger.info(f"Start monitoring memory usage")
        container_id = task_run.id
        container = cls.client.containers.get(container_id=container_id)
        attrs = container.attrs
        pid = attrs["State"]["Pid"]

        process = subprocess.run(
            ["cat", f"/proc/{pid}/cgroup"],
            capture_output=True,
            universal_newlines=True,
            bufsize=1,
        )
        cgroup_pid_path = process.stdout.lstrip("0:").rstrip()
        max_memory_usage = 0
        logging_interval = time.time()
        while os.path.exists(f"/proc/{pid}/status"):
            process = subprocess.run(
                ["cat", f"/sys/fs/cgroup/{cgroup_pid_path}/memory.peak"],
                capture_output=True,
            )
            memory_peak = int(process.stdout.decode("utf-8"))
            max_memory_usage = max(memory_peak, max_memory_usage)

            if abs(time.time() - logging_interval) >= 1:
                cls._logger.info(
                    f"Memory peak: {human_readable_size(max_memory_usage)}"
                )
                logging_interval = time.time()
            time.sleep(0.1)

        return max_memory_usage
