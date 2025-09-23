from task_api.runners.KubernetesRunner import KubernetesRunner
from task_api.processing_container.common import get_task_template, merge_env
from task_api.processing_container import task_models, pc_models
from airflow.models import BaseOperator
from airflow.exceptions import AirflowException
from typing import List, Dict, Any, Optional
from airflow.utils.context import Context
from pathlib import Path
import pickle
import os
import signal
import shutil
from datetime import timedelta
from pydantic import BaseModel, ConfigDict

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator

HOST_WORKFLOW_DIR = Path("/home/kaapana/workflows/data")
AIRFLOW_WORKFLOW_DIR = Path("/kaapana/mounted/workflows/data")
DEFAULT_NAMESPACE = "project-admin"
USER_INPUT_KEY = "task_form"


class IOMapping(BaseModel):
    upstream_operator: BaseOperator
    upstream_channel: str
    downstream_channel: str
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )


class KaapanaTaskOperator(BaseOperator):
    def __init__(
        self,
        image: str,
        taskTemplate: str,
        env: list = [],
        command: Optional[List] = None,
        resources: Optional[pc_models.Resources] = None,
        registryUrl: Optional[str] = None,
        registryUsername: Optional[str] = None,
        registryPassword: Optional[str] = None,
        iochannel_maps: List[IOMapping] = [],
        *args,
        **kwargs,
    ):
        """
        :param iochannel_map: {<upstream-task_id>: {<upstream-output-channel>: <input-channel>}}
        """
        super().__init__(retry_delay=timedelta(seconds=10), *args, **kwargs)
        self.image = image
        self.taskTemplate = taskTemplate
        self.env = env
        self.command = command
        self.resources = resources
        self.registryUrl = registryUrl
        self.registryUsername = registryUsername
        self.registryPassword = registryPassword
        self.iochannel_maps = iochannel_maps

    def execute(self, context: Context) -> Any:
        dag_run_id = context["dag_run"].run_id
        self.host_workflow_dir = HOST_WORKFLOW_DIR / dag_run_id
        self.airflow_workflow_dir = AIRFLOW_WORKFLOW_DIR / dag_run_id
        self.set_namespace(context)
        os.makedirs(self.airflow_workflow_dir, exist_ok=True)

        # Step 3: Create task.pkl
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
        Save the task_run pkl file in the workflow directory
        """
        output = self.airflow_workflow_dir / f"task_run-{self.task_id}.pkl"
        KubernetesRunner.dump(self.task_run, output)

    def _create_task(self, context: Context) -> task_models.Task:
        # Set outputs based on task_template
        # Remove existing output directories on the host
        task_template = get_task_template(
            image=self.image,
            task_identifier=self.taskTemplate,
            mode="k8s",
            namespace=self.namespace,
            registry_secret="registry-secret",
        )
        outputs = []
        for channel in task_template.outputs:
            scheduler_path = Path(
                self.airflow_workflow_dir / self.task_id / channel.name
            )
            if scheduler_path.exists() and scheduler_path.is_dir():
                shutil.rmtree(scheduler_path)

            outputs.append(
                task_models.IOVolume(
                    name=channel.name,
                    input=task_models.HostPathVolume(
                        host_path=str(
                            Path(self.host_workflow_dir / self.task_id / channel.name)
                        ),
                    ),
                )
            )
        inputs = []
        for io_map in self.iochannel_maps:
            task_id = io_map.upstream_operator.task_id
            with open(
                self.airflow_workflow_dir / Path(f"task_run-{task_id}.pkl"), "rb"
            ) as f:
                task_run = pickle.load(f)

            for channel in task_run.outputs:
                if channel.name != io_map.upstream_channel:
                    continue
                inputs.append(
                    task_models.IOVolume(
                        name=io_map.downstream_channel,
                        input=task_models.HostPathVolume(
                            host_path=channel.input.host_path
                        ),
                    )
                )

        task = task_models.Task(
            name=KaapanaBaseOperator.unique_task_identifer(context),
            image=self.image,
            taskTemplate=self.taskTemplate,
            env=self.env,
            command=self.command,
            outputs=outputs,
            inputs=inputs,
            resources=self.resources,
            config=task_models.K8sConfig(
                namespace=self.namespace,
                registryUrl=self.registryUrl,
                registryUsername=self.registryUsername,
                registryPassword=self.registryPassword,
                imagePullSecrets=["registry-secret"],
            ),
        )

        return self._merge_user_input(context, task)

    def _merge_user_input(
        self, context: Context, task: task_models.Task
    ) -> task_models.Task:
        conf = context["dag_run"].conf
        user_input = conf.get(USER_INPUT_KEY, {}).get(self.task_id, {})
        env = merge_env(
            task.env,
            [task_models.TaskInstanceEnv(**env) for env in user_input.pop("env", [])],
        )
        return task_models.Task(
            **{**task.model_dump(mode="python", exclude=["env"]), **user_input}, env=env
        )

    def _submit_task(self, task: task_models.Task) -> task_models.TaskRun:
        return KubernetesRunner.run(task)

    def _monitor_task(self, task_run):
        KubernetesRunner.logs(task_run, follow=True)

    def on_kill(self):
        """
        Make sure that the corresponding pod is removed.
        """
        KubernetesRunner.stop(self.task_run)
        self.log.info("Pod deleted successfully!")

    def set_namespace(self, context):
        conf = context["dag_run"].conf
        print(f"{conf=}")
        project_form = conf.get("project_form", {})
        self.namespace = project_form.get("kubernetes_namespace", DEFAULT_NAMESPACE)
        print(f"{self.namespace=}")
