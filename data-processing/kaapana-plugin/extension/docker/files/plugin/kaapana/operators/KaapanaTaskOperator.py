from taskctl.runners import KubernetesRunner
from taskctl.cli import get_processing_container_json, recursively_merge_dicts
from taskctl.model import Task, TaskRun, IOChannel, Resources
from airflow.models import BaseOperator
from typing import List, Dict, Any, Optional
from airflow.utils.context import Context
from pathlib import Path
import json
import os

ROOT_WORKFLOW_DIR = Path("/home/kaapana/workflows/data")
OUTPUT_CHANNEL_KEY = "output_channel"
DEFAULT_NAMESPACE = "project-admin"


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
        super().__init__(*args, **kwargs)
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
        self.workflow_dir = ROOT_WORKFLOW_DIR / dag_run_id
        os.makedirs(self.workflow_dir)

        # Step 3: Create task.json
        task = self._create_task(context)

        # Step 4: Trigger task
        task_run = self._submit_task(task)

        with open(self.workflow_dir / f"task_run-{self.task_id}.json", "w") as f:
            json.dump(
                task_run.model_dump(
                    mode="json",
                    exclude={"full_object"},
                    exclude_none=True,
                    exclude_unset=True,
                    exclude_defaults=True,
                ),
                f,
            )

        # Step 5: Monitor until complete
        result = self._monitor_task(task_run)

        return result

    def _create_task(self, context: Context) -> Task:

        # Set outputs based on processing_container_json
        processing_container_json = get_processing_container_json(
            self.image, mode="k8s"
        )
        outputs = {
            channel: IOChannel(
                labels=output.get("labels"),
                mounted_path=output.get("mounted_path"),
                local_path=str(Path(self.workflow_dir / self.task_id / channel)),
            )
            for channel, output in processing_container_json.get("outputs").items()
        }
        # Set inputs based on upstream tasks and iochannel_map
        upstream_task_ids = self.get_direct_relative_ids(upstream=True)
        inputs = {}
        for task_id in upstream_task_ids:
            if task_id not in self.iochannel_map:
                continue
            with open(self.workflow_dir / Path(f"task_run-{task_id}.json"), "r") as f:
                task_run = TaskRun(**json.load(f))

            for channel, output in task_run.outputs.items():
                if channel not in self.iochannel_map[task_id]:
                    continue
                inputs[channel] = IOChannel(local_path=output.local_path)

        # Set the namespace based on conf object
        conf = context["dag_run"].conf
        namespace = conf.get("project_form", {}).get(
            "kubernetes_namespace", DEFAULT_NAMESPACE
        )

        task = Task(
            name=self.task_id,
            image=self.image,
            env=self.env,
            command=self.command,
            outputs=outputs,
            inputs=inputs,
            namespace=namespace,
            resources=self.resources,
            registryUrl=self.registryUrl,
            registryUsername=self.registryUsername,
            registryPassword=self.registryPassword,
            imagePullSecrets=["registry-secret"],
        )

        return Task(
            **recursively_merge_dicts(
                processing_container_json,
                task.model_dump(mode="pytohn", exclude_none=True),
            )
        )

    def _submit_task(self, task_json) -> TaskRun:
        return KubernetesRunner.run_task_in_k8s(task_json)

    def _monitor_task(self, task_run):
        KubernetesRunner.task_logs(task_run, follow=True, logger=self.log)
