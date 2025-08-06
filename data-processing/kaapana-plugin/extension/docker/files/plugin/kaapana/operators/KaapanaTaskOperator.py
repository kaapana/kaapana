from taskctl.runners import KubernetesRunner
from taskctl.cli import get_processing_container_json, recursively_merge_dicts
from taskctl.model import Task, TaskRun, IOChannel, Resources
from airflow.models import BaseOperator
from airflow.exceptions import AirflowException
from typing import List, Dict, Any, Optional
from airflow.utils.context import Context
from pathlib import Path
import json
import os
import signal
import shutil
from datetime import timedelta

HOST_WORKFLOW_DIR = Path("/home/kaapana/workflows/data")
AIRFLOW_WORKFLOW_DIR = Path("/kaapana/mounted/workflows/data")
DEFAULT_NAMESPACE = "project-admin"
USER_INPUT_KEY = "task_form"


class KaapanaTaskOperator(BaseOperator):
    def __init__(
        self,
        image: str,
        env: Dict[str, str] = {},
        command: Optional[List] = None,
        resources: Optional[Resources] = None,
        registryUrl: Optional[str] = None,
        registryUsername: Optional[str] = None,
        registryPassword: Optional[str] = None,
        iochannel_map: Dict[str, Dict[str, str]] = {},
        *args,
        **kwargs,
    ):
        """
        :param iochannel_map: {<upstream-task_id>: {<upstream-output-channel>: <input-channel>}}
        """
        super().__init__(retry_delay=timedelta(seconds=10), *args, **kwargs)
        self.image = image
        self.env = env
        self.command = command
        self.resources = resources
        self.registryUrl = registryUrl
        self.registryUsername = registryUsername
        self.registryPassword = registryPassword
        self.iochannel_map = iochannel_map

    def execute(self, context: Context) -> Any:
        dag_run_id = context["dag_run"].run_id
        self.host_workflow_dir = HOST_WORKFLOW_DIR / dag_run_id
        self.airflow_workflow_dir = AIRFLOW_WORKFLOW_DIR / dag_run_id
        os.makedirs(self.airflow_workflow_dir, exist_ok=True)

        # Step 3: Create task.json
        task = self._create_task(context)

        # Step 4: Trigger task
        self.task_run = self._submit_task(task)
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        self._save_task_run()

        # Step 5: Monitor until complete
        result = self._monitor_task(self.task_run)
        return result

    def handle_sigterm(self, signum, frame):
        self.on_kill()
        raise AirflowException("Task was killed gracefully.")

    def _save_task_run(self):
        """
        Save the task_run json file in the workflow directory
        """
        with open(
            self.airflow_workflow_dir / f"task_run-{self.task_id}.json", "w"
        ) as f:
            json.dump(
                self.task_run.model_dump(
                    mode="json",
                    exclude={"full_object"},
                    exclude_none=True,
                    exclude_unset=True,
                    exclude_defaults=True,
                ),
                f,
            )

    def _create_task(self, context: Context) -> Task:
        # Set outputs based on processing_container_json
        # Remove existing output directories on the host
        processing_container_json = get_processing_container_json(
            self.image, mode="k8s"
        )
        outputs = {}
        for channel, output in processing_container_json.get("outputs").items():
            scheduler_path = Path(self.airflow_workflow_dir / self.task_id / channel)
            if scheduler_path.exists() and scheduler_path.is_dir():
                shutil.rmtree(scheduler_path)

            outputs[channel] = IOChannel(
                labels=output.get("labels"),
                mounted_path=output.get("mounted_path"),
                local_path=str(Path(self.host_workflow_dir / self.task_id / channel)),
            )

        # Set inputs based on upstream tasks and iochannel_map
        upstream_task_ids = self.get_direct_relative_ids(upstream=True)
        inputs = {}
        for task_id in upstream_task_ids:
            if task_id not in self.iochannel_map:
                continue
            with open(
                self.airflow_workflow_dir / Path(f"task_run-{task_id}.json"), "r"
            ) as f:
                task_run = TaskRun(**json.load(f))

            for channel, output in task_run.outputs.items():
                if channel not in self.iochannel_map[task_id]:
                    continue
                inputs[channel] = IOChannel(local_path=output.local_path)

        task = Task(
            name=self.task_id,
            image=self.image,
            env=self.env,
            command=self.command,
            outputs=outputs,
            inputs=inputs,
            namespace=DEFAULT_NAMESPACE,
            resources=self.resources,
            registryUrl=self.registryUrl,
            registryUsername=self.registryUsername,
            registryPassword=self.registryPassword,
            imagePullSecrets=["registry-secret"],
        )

        overwrite_with_user_input = self._merge_user_input(context, task)

        return Task(
            **recursively_merge_dicts(
                processing_container_json,
                overwrite_with_user_input.model_dump(mode="pytohn", exclude_none=True),
            )
        )

    def _merge_user_input(self, context: Context, task: Task) -> Task:
        conf = context["dag_run"].conf
        user_input = conf.get(USER_INPUT_KEY, {})

        return Task(
            **recursively_merge_dicts(task.model_dump(mode="python"), user_input)
        )

    def _submit_task(self, task_json) -> TaskRun:
        return KubernetesRunner.run_task_in_k8s(task_json)

    def _monitor_task(self, task_run):
        KubernetesRunner.task_logs(task_run, follow=True, logger=self.log)

    def on_kill(self):
        """
        Make sure that the corresponding pod is removed.
        """
        KubernetesRunner.kill_pod(self.task_run)
        self.log.info("Pod deleted successfully!")
