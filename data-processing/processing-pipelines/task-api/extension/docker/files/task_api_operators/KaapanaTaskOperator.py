from task_api.runners.KubernetesRunner import KubernetesRunner
from task_api.processing_container.common import get_task_template, merge_env
from task_api.processing_container import task_models, pc_models
from airflow.models import BaseOperator
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.operators.python import get_current_context
from typing import List, Dict, Any, Optional
from airflow.utils.context import Context
from pathlib import Path
import pickle
import os
import signal
import shutil
from datetime import timedelta
from pydantic import BaseModel, ConfigDict
from kubernetes import client
from kubernetes.client.exceptions import ApiException


from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator

HOST_WORKFLOW_DIR = Path(os.getenv("DATADIR", "/home/kaapana/workflows/data"))
AIRFLOW_HOME = Path(os.getenv("AIRFLOW_HOME"),"/kaapana/mounted/workflows")
AIRFLOW_WORKFLOW_DIR = Path(AIRFLOW_HOME, "data")
DEFAULT_NAMESPACE = "project-admin"
USER_INPUT_KEY = "task_form"


class IOMapping(BaseModel):
    """
    Represents a mapping between the output of one Airflow task and
    the input of another within a Kaapana workflow.

    This model defines how data is passed between tasks in the workflow DAG
    using specific I/O channels. Each mapping connects a given output channel
    of an upstream task to a corresponding input channel of a downstream task.

    Attributes:
        upstream_operator (BaseOperator):
            The upstream Airflow operator whose output is being used.
        upstream_output_channel (str):
            The name of the output channel of the task template used in the upstream operator.
        input_channel (str):
            The name of the input channel of the task template used in the operator.
    """

    upstream_operator: BaseOperator
    upstream_output_channel: str
    input_channel: str
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )


KAAPANA_ENVIRONMENT = [
    client.V1EnvVar(name="KAAPANA_SERVICES_NAMESPACE", value="services"),
    client.V1EnvVar(name="KAAPANA_ADMIN_NAMESPACE", value="admin"),
    client.V1EnvVar(name="KAAPANA_LOG_LEVEL", value="DEBUG"),
    client.V1EnvVar(name="KAAPANA_TIMEZONE", value="Europe/Berlin"),
    client.V1EnvVar(
        name="KAAPANA_KEYCLOAK_URL",
        value="http://keycloak-external-service.admin.svc:80",
    ),
    client.V1EnvVar(
        name="KAAPANA_CLIENT_SECRET",
        value_from=client.V1EnvVarSource(
            secret_key_ref=client.V1SecretKeySelector(
                name="oidc-client-secret",
                key="oidc-client-secret",
            )
        ),
    ),
    client.V1EnvVar(name="KAAPANA_CLIENT_ID", value="kaapana"),
    client.V1EnvVar(
        name="KAAPANA_OPENSEARCH_HOST", value="opensearch-service.services.svc"
    ),
    client.V1EnvVar(name="KAAPANA_OPENSEARCH_PORT", value="9200"),
    client.V1EnvVar(name="KAAPANA_DEFAULT_OPENSEARCH_INDEX", value="project_admin"),
    client.V1EnvVar(
        name="KAAPANA_PROJECT_USER_PASSWORD",
        value_from=client.V1EnvVarSource(
            secret_key_ref=client.V1SecretKeySelector(
                name="project-user-credentials",
                key="project-user-password",
            )
        ),
    ),
    client.V1EnvVar(
        name="KAAPANA_PROJECT_USER_NAME",
        value_from=client.V1EnvVarSource(
            secret_key_ref=client.V1SecretKeySelector(
                name="project-user-credentials",
                key="project-user",
            )
        ),
    ),
    client.V1EnvVar(
        name="KAAPANA_AII_URL", value="http://aii-service.services.svc:8080"
    ),
    client.V1EnvVar(
        name="KAAPANA_DICOM_WEB_FILTER_URL",
        value="http://dicom-web-filter-service.services.svc:8080",
    ),
    client.V1EnvVar(
        name="KAAPANA_OPENSEARCH_URL",
        value="http://opensearch-service.services.svc:9200",
    ),
    client.V1EnvVar(
        name="KAAPANA_BACKEND_URL",
        value="http://kaapana-backend-service.services.svc:5000",
    ),
    client.V1EnvVar(
        name="KAAPANA_MINIO_URL", value="http://minio-service.services.svc:9000"
    ),
    client.V1EnvVar(
        name="KAAPANA_NOTIFICATION_URL",
        value="http://notification-service.services.svc:80",
    ),
]


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
        startup_timeout_seconds: int = 3600,
        execution_timeout: timedelta = timedelta(minutes=90),
        labels: Dict = {},
        *args,
        **kwargs,
    ):
        """
        An Airflow operator for executing Kaapana tasks within a Kubernetes environment.

        The `KaapanaTaskOperator` handles the full lifecycle of a Kaapana processing
        task: creating the task definition, preparing input/output volumes,
        submitting the task to a to the Kubernetes cluster, and monitoring its execution.
        It strongly utilizes the taskAPI library from Kaapana.

        This operator is typically used as part of a Kaapana workflow DAG, where
        multiple tasks communicate through defined I/O mappings.

        Args:
            image (str):
                The processing-container image used to execute the task.
            taskTemplate (str):
                The identifier of the task template to use in the processing-container.json file.
            env (list, optional):
                A list of environment variable definitions to inject into the container. Overwrites the default values in the task template.
            command (List, optional):
                A list representing the command to execute in the container. Overwrites the default command in the task template.
            resources (pc_models.Resources, optional):
                Resource configuration (e.g., CPU, memory) for the Kubernetes pod.
            registryUrl (str, optional):
                URL of the container registry used to pull the task image.
            registryUsername (str, optional):
                Username for the container registry.
            registryPassword (str, optional):
                Password for the container registry.
            iochannel_maps (List[IOMapping], optional):
                A list of I/O mappings defining data flow between this task and others.
        """
        super().__init__(
            retry_delay=timedelta(seconds=10),
            on_failure_callback=KaapanaTaskOperator.on_failure,
            on_retry_callback=KaapanaTaskOperator.on_retry,
            *args,
            **kwargs,
        )
        self.image = image
        self.taskTemplate = taskTemplate
        self.env = env
        self.command = command
        self.resources = resources
        self.registryUrl = registryUrl
        self.registryUsername = registryUsername
        self.registryPassword = registryPassword
        self.iochannel_maps = iochannel_maps
        self.startup_timeout_seconds = startup_timeout_seconds
        self.execution_timeout = execution_timeout
        self.labels = labels

    def execute(self, context: Context) -> Any:
        dag_run_id = context["dag_run"].run_id
        self.host_workflow_dir = HOST_WORKFLOW_DIR / dag_run_id
        self.airflow_workflow_dir = AIRFLOW_WORKFLOW_DIR / dag_run_id
        self.task_run_file = KaapanaTaskOperator.task_run_file_path(context)
        self.set_namespace(context)
        os.makedirs(self.airflow_workflow_dir, exist_ok=True)

        # Step 3: Create task.pkl
        task = self._create_task(context)

        # Step 4: Trigger task
        self.task_run = self._submit_task(task)
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        self._save_task_run()

        # Step 5: Monitor until complete
        result = self._monitor_task_run()
        return result

    def handle_sigterm(self, signum, frame):
        self.on_kill()
        raise AirflowException("Task was killed gracefully.")

    def _save_task_run(self):
        """
        Save the task_run pkl file in the workflow directory
        """
        KubernetesRunner.dump(self.task_run, self.task_run_file)

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
                    volume_source=task_models.HostPathVolume(
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
                if channel.name != io_map.upstream_output_channel:
                    continue
                inputs.append(
                    task_models.IOVolume(
                        name=io_map.input_channel,
                        volume_source=task_models.HostPathVolume(
                            host_path=channel.volume_source.host_path
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
                env_vars=KAAPANA_ENVIRONMENT,
                labels={
                    "kaapana.type": "processing-container",
                    "pod-type": "processing-container",
                    **self.labels,
                },
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
            [pc_models.BaseEnv(**env) for env in user_input.pop("env", [])],
        )
        return task_models.Task(
            **{**task.model_dump(mode="python", exclude=["env"]), **user_input}, env=env
        )

    def _submit_task(self, task: task_models.Task) -> task_models.TaskRun:
        try:
            return KubernetesRunner.run(task)
        except ApiException as e:
            KubernetesRunner._logger.warning(
                f"Submitting task to k8s API failed: {e.reason} -> Try to delete conflicting pod."
            )
        try:
            KaapanaTaskOperator.stop_task_pod()
            return KubernetesRunner.run(task)
        except ApiException as e:
            KubernetesRunner._logger.error(
                f"Submitting task to k8s API is stillg failing: {e.reason}."
            )
            raise e

    def _monitor_task_run(self):
        try:
            KubernetesRunner.logs(
                self.task_run,
                follow=True,
                startup_timeout=self.startup_timeout_seconds,
                log_timeout=self.execution_timeout.total_seconds(),
            )
        except TimeoutError:
            final_status = KubernetesRunner.wait_for_task_status(
                self.task_run,
                states=["Pending", "Running", "Terminating"],
                timeout=5,
            )
            if final_status == "Running":
                raise AirflowException(
                    f"Processing container didn't finish in execution timeout: {self.execution_timeout.total_seconds()} seconds. The corresponding will be deleted!"
                )
            elif final_status == "Pending":
                raise AirflowException(
                    f"Processing container didn't start within {self.startup_timeout_seconds} seconds. The corresponding will be deleted!"
                )
            else:
                raise AirflowException(
                    f"Processing container in unexpected state: {final_status}"
                )

        final_status = KubernetesRunner.wait_for_task_status(
            self.task_run,
            states=["Succeeded", "Failed"],
            timeout=30,
        )
        if final_status == "Failed":
            pod = KubernetesRunner.api.read_namespaced_pod(
                name=self.task_run.id, namespace=self.task_run.config.namespace
            )

            container_name = "main"
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if cs.name == container_name:
                        state = cs.state
                        if state.terminated:
                            exit_code = state.terminated.exit_code
                            message = state.terminated.message
                            reason = state.terminated.reason
                        else:
                            raise AirflowException(
                                f"Kubernetes status {final_status} but container {container_name} not terminated"
                            )
                        break
            else:
                raise AirflowException(
                    f"Could not read final container status for pod {pod.name} and container {container_name}"
                )
            if reason == "OOMKilled":
                raise AirflowException(
                    f"Container {container_name} for task {self.task_run.name} was terminated due to OutOfMemory (OOMKilled)"
                )
            if exit_code == 126:
                raise AirflowSkipException(
                    f"Task {self.task_run.name} was skipped, {reason=}, {message=}"
                )
            elif exit_code != 0:
                raise AirflowException(
                    f"Processing container failed for task {self.task_run.name}!"
                )
        elif final_status == "Succeeded":
            self.log.info(f"Processing Container finished successfully!")
        else:
            raise AirflowException(
                f"Processing container in unexpected state: {final_status}"
            )

    def on_kill(self):
        """
        Make sure that the corresponding pod is removed.
        """
        KubernetesRunner.stop(self.task_run)
        self.log.info("Pod deleted successfully!")

    def set_namespace(self, context: Context):
        conf = context["dag_run"].conf
        project_form = conf.get("project_form", {})
        self.namespace = project_form.get("kubernetes_namespace", DEFAULT_NAMESPACE)

    @staticmethod
    def stop_task_pod(context: Context = None):
        context = context or get_current_context()
        try:
            with open(KaapanaTaskOperator.task_run_file_path(context), "rb") as f:
                task_run = pickle.load(f)
                KubernetesRunner.stop(task_run=task_run)
            KubernetesRunner._logger.info(
                f"Stopped processing-container: {task_run.id}"
            )
        except FileNotFoundError:
            KubernetesRunner._logger.info("Task File not found")
        except client.ApiException as e:
            KubernetesRunner._logger.warning(f"Kubernetes API exception: {e}")
        finally:
            return None

    @staticmethod
    def on_failure(context: Context):
        KaapanaTaskOperator.stop_task_pod(context)

    @staticmethod
    def on_retry(context: Context):
        KaapanaTaskOperator.stop_task_pod(context)

    @staticmethod
    def task_run_file_path(context: Context):
        """
        Return the path to the file, where the TaskInstance object will be stored.

        :param context: Dictionary set by Airflow. It contains references to related objects to the task instance.
        """
        task_id = context["task"].task_id
        return Path(AIRFLOW_WORKFLOW_DIR, context["run_id"], f"task_run-{task_id}.pkl")
