import os
import pickle
import shutil
import signal
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.models import BaseOperator
from airflow.operators.python import get_current_context
from airflow.utils.context import Context
from kaapana.blueprints.kaapana_utils import get_release_name
from kubernetes import client
from kubernetes.client.exceptions import ApiException
from pydantic import BaseModel, ConfigDict
from task_api.processing_container import pc_models, task_models
from task_api.processing_container.common import (
    create_task_instance,
    get_task_template,
    merge_env,
)
from task_api.runners.KubernetesRunner import KubernetesRunner, PodPhase

HOST_WORKFLOW_DIR = Path(os.getenv("DATADIR", "/home/kaapana/workflows/data"))
AIRFLOW_HOME = Path(os.getenv("AIRFLOW_HOME"), "/kaapana/mounted/workflows")
AIRFLOW_WORKFLOW_DIR = Path(AIRFLOW_HOME, "data")
DEFAULT_NAMESPACE = "project-admin"
ADMIN_NAMESPACE = os.getenv("ADMIN_NAMESPACE", "admin")
SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE", "services")
KAAPANA_BUILD_VERSION = os.getenv("KAAPANA_BUILD_VERSION")
HELM_API = f"http://kube-helm-service.{ADMIN_NAMESPACE}.svc:5000"
USER_INPUT_KEY = "task_form"
KAAPANA_SKIP_TASK_RUN_RETURN_CODE = 126
DEV_SERVER_TIMEOUT = 60 * 60 * 12


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
        annotations: Optional[Dict[str, str]] = None,
        dev_server: bool = False,
        display_name: str = "-",
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
            annotations (Dict[str, str], optional):
                A dictionary of annotations to add to the Kubernetes pod.
            dev_server (bool, optional):
                Deploy the task image through dev-server-chart instead of running
                the processing pod.
            display_name (str, optional):
                Display name used for the pending dev-server application.
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
        self.annotations = annotations or {}
        self.dev_server = dev_server
        self.display_name = display_name

    def execute(self, context: Context) -> Any:
        dag_run_id = context["dag_run"].run_id
        self.host_workflow_dir = HOST_WORKFLOW_DIR / dag_run_id
        self.airflow_workflow_dir = AIRFLOW_WORKFLOW_DIR / dag_run_id
        self.task_run_file = KaapanaTaskOperator.task_run_file_path(context)
        self.set_namespace(context)
        os.makedirs(self.airflow_workflow_dir, exist_ok=True)

        # Step 3: Create task.pkl
        task = self._create_task(context)

        if self.dev_server:
            return self._launch_dev_server(context, task)

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
            name=KaapanaTaskOperator.unique_task_identifer(context),
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
                    "kaapana.ai/type": "processing-container",
                    **self.labels,
                },
                annotations=self.annotations,
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
                f"Submitting task to k8s API is still failing: {e.reason}."
            )
            raise e

    def _launch_dev_server(self, context: Context, task: task_models.Task):
        task_template = get_task_template(
            image=task.image,
            task_identifier=task.taskTemplate,
            mode="k8s",
            namespace=task.config.namespace,
            registry_secret="registry-secret",
        )
        task_instance = create_task_instance(task_template=task_template, task=task)
        release_name = get_release_name(context)
        payload = {
            "name": "dev-server-chart",
            "version": KAAPANA_BUILD_VERSION,
            "release_name": release_name,
            "sets": self._dev_server_helm_sets(context, task_instance),
        }

        self.log.info("Deploying dev-server-chart for task %s", self.task_id)
        r = requests.post(f"{HELM_API}/helm-install-chart", json=payload)
        self.log.info(r.text)
        r.raise_for_status()

        t_end = time.time() + DEV_SERVER_TIMEOUT
        while time.time() < t_end:
            time.sleep(15)
            r = requests.get(
                f"{HELM_API}/view-chart-status",
                params={"release_name": release_name},
            )
            if r.status_code in [500, 404]:
                self.log.info(
                    "Release %s was uninstalled. Dev-server task is done.",
                    release_name,
                )
                return
            r.raise_for_status()

        raise AirflowException(
            f"Dev-server release {release_name} exceeded timeout."
        )

    def _dev_server_helm_sets(
        self, context: Context, task_instance: task_models.TaskInstance
    ) -> Dict[str, Any]:
        env_sets = self._dev_server_env_sets(task_instance)
        secret_env_sets = self._dev_server_secret_env_sets(task_instance)
        label_sets = self._dev_server_label_sets(task_instance)
        volume_sets = self._dev_server_volume_sets(task_instance)
        project_id = self._project_id(context)
        ingress_path = (
            f"applications/project/{project_id}/release/" + "{{ .Release.Name }}"
        )

        return {
            "global.complete_image": task_instance.image,
            "global.namespace": task_instance.config.namespace,
            "global.ingress_path": ingress_path,
            "global.display_name": self.display_name,
            **env_sets,
            **secret_env_sets,
            **label_sets,
            **volume_sets,
        }

    def _dev_server_env_sets(
        self, task_instance: task_models.TaskInstance
    ) -> Dict[str, Any]:
        env_sets = {}
        env_vars = {"WORKSPACE": "/kaapana"}
        for env in [*task_instance.env, *task_instance.config.env_vars]:
            if env.value is not None:
                env_vars[env.name] = env.value

        for idx, (name, value) in enumerate(env_vars.items()):
            env_sets[f"global.envVars[{idx}].name"] = name
            env_sets[f"global.envVars[{idx}].value"] = value
        return env_sets

    def _dev_server_secret_env_sets(
        self, task_instance: task_models.TaskInstance
    ) -> Dict[str, str]:
        secret_sets = {}
        secret_envs = [
            env
            for env in task_instance.config.env_vars
            if env.value_from and env.value_from.secret_key_ref
        ]
        for idx, env in enumerate(secret_envs):
            secret_ref = env.value_from.secret_key_ref
            secret_sets[f"global.envVarsFromSecretRef[{idx}].name"] = env.name
            secret_sets[
                f"global.envVarsFromSecretRef[{idx}].secretName"
            ] = secret_ref.name
            secret_sets[
                f"global.envVarsFromSecretRef[{idx}].secretKey"
            ] = secret_ref.key
        return secret_sets

    def _dev_server_label_sets(
        self, task_instance: task_models.TaskInstance
    ) -> Dict[str, str]:
        label_sets = {}
        for idx, (name, value) in enumerate(task_instance.config.labels.items()):
            label_sets[f"global.labels[{idx}].name"] = str(name)
            label_sets[f"global.labels[{idx}].value"] = str(value)
        return label_sets

    def _dev_server_volume_sets(
        self, task_instance: task_models.TaskInstance
    ) -> Dict[str, str]:
        volumes = []
        for mount in task_instance.config.volume_mounts:
            if mount.name == "dshm":
                continue
            volumes.append(
                {
                    "name": mount.name,
                    "mount_path": mount.mount_path,
                    "sub_path": mount.sub_path,
                }
            )

        for channel in [*task_instance.inputs, *task_instance.outputs]:
            if not isinstance(
                channel.volume_source, task_models.PersistentVolumeClaimVolume
            ):
                continue
            volumes.append(
                {
                    "name": channel.volume_source.persistent_volume_claim.claim_name.replace(
                        "-pv-claim", ""
                    ),
                    "mount_path": channel.mounted_path,
                    "sub_path": channel.volume_source.sub_path,
                }
            )

        volume_sets = {}
        for idx, volume in enumerate(volumes):
            volume_sets[f"global.dynamicVolumes[{idx}].name"] = volume["name"]
            volume_sets[f"global.dynamicVolumes[{idx}].mount_path"] = volume[
                "mount_path"
            ]
            if volume["sub_path"]:
                volume_sets[f"global.dynamicVolumes[{idx}].sub_path"] = volume[
                    "sub_path"
                ]
        return volume_sets

    def _project_id(self, context: Context) -> str:
        conf = context["dag_run"].conf or {}
        project_form = conf.get("project_form", {})
        if project_form.get("id"):
            return project_form["id"]

        response = requests.get(f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/admin")
        response.raise_for_status()
        return response.json().get("id")

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
                states=[PodPhase.PENDING, PodPhase.RUNNING],
                timeout=5,
            )
            if final_status == PodPhase.RUNNING:
                raise AirflowException(
                    f"Processing container didn't finish in execution timeout: {self.execution_timeout.total_seconds()} seconds. The corresponding pod will be deleted!"
                )
            elif final_status == PodPhase.PENDING:
                raise AirflowException(
                    f"Processing container didn't start within {self.startup_timeout_seconds} seconds. The corresponding pod will be deleted!"
                )
            else:
                raise AirflowException(
                    f"Processing container in unexpected state: {final_status}"
                )

        final_status = KubernetesRunner.wait_for_task_status(
            self.task_run,
            states=[PodPhase.SUCCEEDED, PodPhase.FAILED],
            timeout=30,
        )
        if final_status == PodPhase.FAILED:
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
            if exit_code == KAAPANA_SKIP_TASK_RUN_RETURN_CODE:
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
        if not hasattr(self, "task_run"):
            self.log.info("No processing pod to delete.")
            return
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
        if getattr(context["task"], "dev_server", False):
            KaapanaTaskOperator.uninstall_dev_server(context)
        else:
            KaapanaTaskOperator.stop_task_pod(context)

    @staticmethod
    def on_retry(context: Context):
        if getattr(context["task"], "dev_server", False):
            KaapanaTaskOperator.uninstall_dev_server(context)
        else:
            KaapanaTaskOperator.stop_task_pod(context)

    @staticmethod
    def uninstall_dev_server(context: Context):
        release_name = get_release_name(context)
        r = requests.get(
            f"{HELM_API}/view-chart-status",
            params={"release_name": release_name},
        )
        if r.status_code in [500, 404]:
            KubernetesRunner._logger.info(
                f"Release {release_name} was uninstalled or never installed."
            )
            return None

        r.raise_for_status()
        r = requests.post(
            f"{HELM_API}/helm-delete-chart",
            params={"release_name": release_name},
        )
        r.raise_for_status()
        KubernetesRunner._logger.info(f"Deleted dev-server release: {release_name}")
        return None

    @staticmethod
    def task_run_file_path(context: Context):
        """
        Return the path to the file, where the TaskInstance object will be stored.

        :param context: Dictionary set by Airflow. It contains references to related objects to the task instance.
        """
        task_id = context["task"].task_id
        return Path(AIRFLOW_WORKFLOW_DIR, context["run_id"], f"task_run-{task_id}.pkl")

    @staticmethod
    def unique_task_identifer(context: Context):
        """
        Set a unique identifier for this task instance.

        :param context: Dictionary set by Airflow. It contains references to related objects to the task instance.
        """
        return f"{context["ti"].run_id}-{context["ti"].task_id}"
