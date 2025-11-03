import glob
import json
import logging
import os
import re
import shutil
import time
from datetime import datetime, timedelta

import requests
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.models import BaseOperator, Variable
from airflow.models.skipmixin import SkipMixin
from airflow.utils.dates import days_ago
from airflow.utils.state import State
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.context import Context
from kaapana.blueprints.kaapana_global_variables import (
    ADMIN_NAMESPACE,
    AIRFLOW_WORKFLOW_DIR,
    BATCH_NAME,
    DEFAULT_REGISTRY,
    GPU_SUPPORT,
    KAAPANA_BUILD_VERSION,
    PLATFORM_VERSION,
    PROCESSING_WORKFLOW_DIR,
    PULL_POLICY_IMAGES,
)
from kaapana.blueprints.kaapana_utils import cure_invalid_name, get_release_name
from kaapana.operators import HelperSendEmailService
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperFederated import federated_sharing_decorator
from kaapanapy.services.NotificationService import Notification, NotificationService
from kaapanapy.settings import ServicesSettings

import signal
import pickle
from pathlib import Path
from task_api.processing_container import task_models, pc_models
from task_api.runners.KubernetesRunner import KubernetesRunner, PodPhase
from kubernetes import client
from kubernetes import config as k8s_config_loader


KAAPANA_SKIP_TASK_RUN_RETURN_CODE = 126
# Backward compatibility
default_registry = DEFAULT_REGISTRY
kaapana_build_version = KAAPANA_BUILD_VERSION
platform_version = PLATFORM_VERSION


class KaapanaBaseOperator(BaseOperator, SkipMixin):
    """
    Execute a task in a Kubernetes Pod

    :param image: Docker image you wish to launch. Defaults to dockerhub.io,
        but fully qualified URLS will point to custom repositories
    :type image: str
    :param namespace: the namespace to run within kubernetes
    :type namespace: str
    :param cmds: entrypoint of the container. (templated)
        The docker images's entrypoint is used if this is not provide.
    :type cmds: list of str
    :param arguments: arguments of to the entrypoint. (templated)
        The docker image's CMD is used if this is not provided.
    :type arguments: list of str
    :param volume_mounts: volumeMounts for launched pod
    :type volume_mounts: list of VolumeMount
    :param volumes: volumes for launched pod. Includes ConfigMaps and PersistentVolumes
    :type volumes: list of Volume
    :param labels: labels to apply to the Pod
    :type labels: dict
    :param startup_timeout_seconds: timeout in seconds to startup the pod
    :type startup_timeout_seconds: int
    :param name: name of the task you want to run,
        will be used to generate a pod id
    :type name: str
    :param env_vars: Environment variables initialized in the container. (templated)
    :type env_vars: dict
    :param secrets: Kubernetes secrets to inject in the container,
        They can be exposed as environment vars or files in a volume.
    :type secrets: list of Secret
    :param in_cluster: run kubernetes client with in_cluster configuration
    :type in_cluster: bool
    :param cluster_context: context that points to kubernetes cluster.
        Ignored when in_cluster is True. If None, current-context is used.
    :type cluster_context: string
    :param get_logs: get the stdout of the container as logs of the tasks
    :type get_logs: bool
    :param affinity: A dict containing a group of affinity scheduling rules
    :type affinity: dict
    :param node_selectors: A dict containing a group of scheduling rules
    :type node_selectors: dict
    :param tolerations: A V1Toleration list specifying pod tolerations
    :type node_selectors: list[V1Toleration]
    :param config_file: The path to the Kublernetes config file
    :type config_file: str
    :param xcom_push: If xcom_push is True, the content of the file
        /airflow/xcom/return.json in the container will also be pushed to an
        XCom when the container completes.
    :type xcom_push: bool
    """

    HELM_API = f"http://kube-helm-service.{ADMIN_NAMESPACE}.svc:5000"
    TIMEOUT = 60 * 60 * 12
    CURE_INVALID_NAME_REGEX = r"[a-z]([-a-z0-9]*[a-z0-9])?"

    def __init__(
        self,
        dag,
        name,
        image=None,
        # Directories
        input_operator=None,
        operator_in_dir=None,
        operator_out_dir=None,
        # Airflow
        task_id=None,
        parallel_id=None,
        keep_parallel_id=True,
        trigger_rule=TriggerRule.ALL_SUCCESS,
        ram_mem_mb=500,
        ram_mem_mb_lmt=None,
        cpu_millicores=None,
        cpu_millicores_lmt=None,
        gpu_mem_mb=None,
        gpu_mem_mb_lmt=None,
        retries=1,
        retry_delay=timedelta(seconds=30),
        execution_timeout=timedelta(minutes=90),
        max_active_tis_per_dag=None,
        manage_cache=None,
        allow_federated_learning=False,
        whitelist_federated_learning=None,
        delete_input_on_success=False,
        delete_output_on_start=True,
        # Other stuff
        enable_proxy=False,
        no_proxy=None,
        batch_name=None,
        airflow_workflow_dir=None,
        cmds=None,
        arguments=None,
        env_vars=None,
        image_pull_secrets=None,
        priority_weight=1,
        priority_class_name="kaapana-low-priority",
        startup_timeout_seconds=3600,
        namespace=None,
        image_pull_policy=PULL_POLICY_IMAGES,
        #  Deactivated till dynamic persistent volumes are supported
        #  volume_mounts=None,
        #  volumes=None,
        pod_resources=None,
        in_cluster=False,
        cluster_context=None,
        labels=None,
        get_logs=True,
        annotations=None,
        affinity=None,
        config_file=None,
        xcom_push=False,
        node_selectors=None,
        tolerations=None,
        secrets=None,
        kind="Pod",
        pool=None,
        pool_slots=None,
        api_version="v1",
        dev_server=None,
        display_name="-",  # passed to the dev-server chart as display_name annotation for the ingress
        **kwargs,
    ):
        #  Deactivated till dynamic persistent volumes are supported
        volume_mounts = None
        volumes = None

        KaapanaBaseOperator.set_defaults(
            self,
            name=name,
            task_id=task_id,
            operator_out_dir=operator_out_dir,
            input_operator=input_operator,
            operator_in_dir=operator_in_dir,
            parallel_id=parallel_id,
            keep_parallel_id=keep_parallel_id,
            trigger_rule=trigger_rule,
            pool=pool,
            pool_slots=pool_slots,
            ram_mem_mb=ram_mem_mb,
            ram_mem_mb_lmt=ram_mem_mb_lmt,
            cpu_millicores=cpu_millicores,
            cpu_millicores_lmt=cpu_millicores_lmt,
            gpu_mem_mb=gpu_mem_mb,
            gpu_mem_mb_lmt=gpu_mem_mb_lmt,
            manage_cache=manage_cache,
            allow_federated_learning=allow_federated_learning,
            whitelist_federated_learning=whitelist_federated_learning,
            batch_name=batch_name,
            airflow_workflow_dir=airflow_workflow_dir,
            delete_input_on_success=delete_input_on_success,
            delete_output_on_start=delete_output_on_start,
            priority_class_name=priority_class_name,
        )

        # Airflow
        self.retries = retries
        self.priority_weight = priority_weight
        self.execution_timeout = execution_timeout
        self.max_active_tis_per_dag = max_active_tis_per_dag
        self.retry_delay = retry_delay

        # helm
        if dev_server not in [None, "code-server"]:
            raise NameError("dev_server must be either None or code-server!")
        if dev_server is not None:
            self.execution_timeout = None
        self.dev_server = dev_server

        # Kubernetes
        self.image = image
        self.env_vars = env_vars or {}
        self.namespace = namespace
        self.cmds = [cmds] if isinstance(cmds, str) else (cmds or [])
        self.arguments = (
            [arguments] if isinstance(arguments, str) else (arguments or [])
        )
        self.labels = labels or {}
        self.labels.update(
            {
                "kaapana.ai/type": "processing-container",
            }
        )
        self.startup_timeout_seconds = startup_timeout_seconds
        self.volume_mounts = volume_mounts or []
        self.volumes = volumes or []
        self.image_pull_secrets = image_pull_secrets or []
        self.in_cluster = in_cluster
        self.cluster_context = cluster_context
        self.get_logs = get_logs
        self.image_pull_policy = image_pull_policy
        self.node_selectors = node_selectors or {}
        self.tolerations = tolerations
        self.annotations = annotations or {}
        self.affinity = affinity or {}
        self.xcom_push = xcom_push
        self.pod_resources = pod_resources or None
        self.config_file = config_file
        self.api_version = api_version
        self.secrets = secrets or []
        self.kind = kind
        self.data_dir = os.getenv("DATADIR", "")
        self.model_dir = os.getenv("MODELDIR", "")
        self.result_message = None
        self.display_name = display_name

        # Namespaces
        self.services_namespace = os.getenv("SERVICES_NAMESPACE", "")
        self.admin_namespace = os.getenv("ADMIN_NAMESPACE", "")

        if self.pod_resources is None:
            self.pod_resources = pc_models.Resources(
                limits={
                    "cpu": (
                        "{}m".format(self.cpu_millicores + 100)
                        if self.cpu_millicores != None
                        else None
                    ),
                    "memory": "{}Mi".format(
                        self.ram_mem_mb_lmt
                        if self.ram_mem_mb_lmt is not None
                        else self.ram_mem_mb + 100
                    ),
                    "nvidia.com/gpu": 1 if self.gpu_mem_mb else 0,
                },
                requests={
                    "cpu": (
                        "{}m".format(self.cpu_millicores)
                        if self.cpu_millicores != None
                        else None
                    ),
                    "memory": "{}Mi".format(self.ram_mem_mb),
                },
            )

        envs = {
            "SERVICES_NAMESPACE": str(self.services_namespace),
            "ADMIN_NAMESPACE": str(self.admin_namespace),
        }

        envs.update(
            {
                "KEYCLOAK_URL": os.environ["KEYCLOAK_URL"],
                "KUBE_HELM_URL": os.environ["KUBE_HELM_URL"],
                "OPENSEARCH_URL": os.environ["OPENSEARCH_URL"],
                "DICOM_WEB_FILTER_URL": os.environ["DICOM_WEB_FILTER_URL"],
                "NOTIFICATION_URL": os.environ["NOTIFICATION_URL"],
                "AII_URL": os.environ["AII_URL"],
                "KAAPANA_BACKEND_URL": os.environ["KAAPANA_BACKEND_URL"],
                "MINIO_URL": os.environ["MINIO_URL"],
            }
        )
        if enable_proxy is True and os.getenv("PROXY", None) is not None:
            envs.update(
                {
                    "http_proxy": os.getenv("PROXY", ""),
                    "https_proxy": os.getenv("PROXY", ""),
                }
            )

        if no_proxy is not None:
            envs.update({"no_proxy": no_proxy})

        if hasattr(self, "operator_in_dir"):
            envs["OPERATOR_IN_DIR"] = str(self.operator_in_dir)

        envs.update(self.env_vars)
        self.env_vars = envs
        super().__init__(
            dag=dag,
            task_id=self.task_id,
            retries=self.retries,
            priority_weight=self.priority_weight,
            execution_timeout=self.execution_timeout,
            max_active_tis_per_dag=self.max_active_tis_per_dag,
            pool=self.pool,
            pool_slots=self.pool_slots,
            retry_delay=self.retry_delay,
            email=None,
            email_on_retry=False,
            email_on_failure=False,
            start_date=days_ago(0),
            depends_on_past=False,
            wait_for_downstream=False,
            trigger_rule=self.trigger_rule,
            on_failure_callback=KaapanaBaseOperator.on_failure,
            on_success_callback=KaapanaBaseOperator.on_success,
            on_retry_callback=KaapanaBaseOperator.on_retry,
            on_execute_callback=KaapanaBaseOperator.on_execute,
            executor_config=self.executor_config,
            **kwargs,
        )

    def clear(
        self,
        start_date=None,
        end_date=None,
        upstream=False,
        downstream=False,
        session=None,
    ):
        self.log.info("##################################################### IN CLEAR!")
        self.log.info(self)
        self.log.info(self.ti)
        self.log.info(self.ti.kube_name)

        super.clear(
            start_date=start_date,
            end_date=end_date,
            upstream=upstream,
            downstream=downstream,
            session=session,
        )

    def set_volumes_and_volume_mounts(self):
        """
        Set volumes and volume claims based on the project namespace self.namespace.
        This function should be called after self.namespace was changed according to the project in the context params.
        """
        volume_volumeMount_pairs = [
            (
                client.V1Volume(
                    name="workflowdata",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=f"{self.namespace}-workflow-data-pv-claim",
                        read_only=False,
                    ),
                ),
                client.V1VolumeMount(
                    name="workflowdata",
                    mount_path=PROCESSING_WORKFLOW_DIR,
                    sub_path=None,
                    read_only=False,
                ),
            ),
            (
                client.V1Volume(
                    name="models",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=f"{self.namespace}-models-pv-claim",
                        read_only=False,
                    ),
                ),
                client.V1VolumeMount(
                    name="models", mount_path="/models", sub_path=None, read_only=False
                ),
            ),
            (
                client.V1Volume(
                    name="tensorboard",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=f"{self.namespace}-tensorboard-pv-claim",
                        read_only=False,
                    ),
                ),
                client.V1VolumeMount(
                    name="tensorboard",
                    mount_path="/tensorboard",
                    sub_path=None,
                    read_only=False,
                ),
            ),
            (
                client.V1Volume(
                    name="dshm",
                    empty_dir=client.V1EmptyDirVolumeSource(medium="Memory"),
                ),
                client.V1VolumeMount(
                    name="dshm", mount_path="/dev/shm", sub_path=None, read_only=False
                ),
            ),
        ]

        for volume, volumeMount in volume_volumeMount_pairs:
            self.volumes.append(volume)
            self.volume_mounts.append(volumeMount)

    def set_env_secrets(self):
        """
        Add env variables that are retrieved from kubernets secrets to self.secrets.
        """
        project_credentials_password = client.V1EnvVar(
            name="KAAPANA_PROJECT_USER_PASSWORD",
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    name="project-user-credentials",
                    key="project-user-password",
                )
            ),
        )

        project_credentials_username = client.V1EnvVar(
            name="KAAPANA_PROJECT_USER_NAME",
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    name="project-user-credentials",
                    key="project-user",
                )
            ),
        )

        oidc_client_secret = client.V1EnvVar(
            name="KAAPANA_CLIENT_SECRET",
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    name="oidc-client-secret",
                    key="oidc-client-secret",
                )
            ),
        )

        self.secrets.extend(
            [
                project_credentials_password,
                project_credentials_username,
                oidc_client_secret,
            ]
        )



    def create_conf_configmap(self, context: Context):
        # Load Kubernetes configuration (in-cluster or local)
        try:
            k8s_config_loader.load_incluster_config()
        except config.config_exception.ConfigException:
            k8s_config_loader.load_kube_config()

        # Extract the configuration
        dag_conf = context["dag_run"].conf or {}
        config_json = json.dumps(dag_conf, indent=4, sort_keys=True)

        # Define metadata
        configmap_name = f"{context["ti"].run_id}-config"

        # Create ConfigMap body
        metadata = client.V1ObjectMeta(
            name=configmap_name,
            namespace=self.namespace,
            labels={"app": "kaapana", "run_id": context["run_id"]},
        )
        body = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=metadata,
            data={"conf.json": config_json},
        )

        # Create the ConfigMap in the cluster
        v1 = client.CoreV1Api()
        try:
            v1.create_namespaced_config_map(namespace=self.namespace, body=body)
            logging.info(f"Created ConfigMap: {configmap_name}")
        except client.exceptions.ApiException as e:
            if e.status == 409:
                logging.info(f"ConfigMap: {configmap_name}, already exists.")
            else:
                raise
            
        volume_conf = client.V1Volume(
                name="workflowconf",
                config_map=client.V1ConfigMapVolumeSource(
                    name=configmap_name,
                    items=[client.V1KeyToPath(key="conf.json", path="conf.json")]
                ),
            )

        volume_mount_conf = client.V1VolumeMount(
                name="workflowconf",
                mount_path=os.path.join(
                    PROCESSING_WORKFLOW_DIR, context["run_id"], "conf", "conf.json"
                ),
                sub_path="conf.json",
                read_only=True,
            ) 
        self.volumes.append(volume_conf)
        self.volume_mounts.append(volume_mount_conf)

    def launch_dev_server(self, context: Context):
        """
        Launch a dev-server as pending application.
        """
        url = f"{KaapanaBaseOperator.HELM_API}/helm-install-chart"

        workflow_form = {}
        if (
            context["dag_run"].conf is not None
            and "workflow_form" in context["dag_run"].conf
            and context["dag_run"].conf["workflow_form"] is not None
        ):
            workflow_form = context["dag_run"].conf["workflow_form"]
            print(f"{workflow_form=}")
        env_vars_sets = {}
        for idx, (k, v) in enumerate(
            {"WORKSPACE": "/kaapana", **self.env_vars}.items()
        ):
            if k.lower() in workflow_form:
                ### Values in workflow_form are converted with str() before storing them in self.env_vars
                ### In order to load them with json.loads later, we use the original value and convert it to a stringified json.
                v = json.dumps(workflow_form[k.lower()])
            try:
                ### Json objects should be send as json-object, not stringified json. Especially needed, when environment variables represent lists, e.g. RUNNER_INSTANCES=["<ip-address>"]
                json_decoded_value = json.loads(v)
            except json.decoder.JSONDecodeError as e:
                json_decoded_value = v
            if type(json_decoded_value) == dict:
                ### kube-helm will use --set-string instead of --set to install the chart when the value is a string
                ### As helm interpretes {} as array/list, we want to use --set-string for enviroment variables that are dictionaries.
                json_decoded_value = str(json_decoded_value)
            env_vars_sets.update(
                {
                    f"global.envVars[{idx}].name": f"{k}",
                    f"global.envVars[{idx}].value": json_decoded_value,
                }
            )

        env_vars_from_secret_key_refs = {}
        for idx, secret in enumerate(self.secrets):
            env_vars_from_secret_key_refs.update(
                {
                    f"global.envVarsFromSecretRef[{idx}].name": secret.name,
                    f"global.envVarsFromSecretRef[{idx}].secretName": secret.value_from.secret_key_ref.name,
                    f"global.envVarsFromSecretRef[{idx}].secretKey": secret.value_from.secret_key_ref.key,
                }
            )

        dynamic_label_sets = {}
        for idx, (labelName, labelValue) in enumerate(self.labels.items()):
            dynamic_label_sets.update(
                {
                    f"global.labels[{idx}].name": str(labelName),
                    f"global.labels[{idx}].value": str(labelValue),
                }
            )

        dynamic_volume_lookup = {}
        configmap_volume_config = {}
        configmap_name = None

        for volume in self.volumes:
            if not volume.persistent_volume_claim:
                if volume.name == "workflowconf" and volume.config_map:
                    configmap_name = volume.config_map.name
                    configmap_volume_config["global.workflow_configmap_name"] = configmap_name
                continue
            dynamic_volume_lookup[volume.name] = {
                "name": volume.persistent_volume_claim.claim_name.replace(
                    "-pv-claim", ""
                )
            }

        for vol_mount in self.volume_mounts:
            if vol_mount.name not in dynamic_volume_lookup:
                if vol_mount.name == "workflowconf":
                    configmap_volume_config["global.workflow_config_mount_path"] = vol_mount.mount_path
                continue
            dynamic_volume_lookup[vol_mount.name]["mount_path"] = vol_mount.mount_path

        dynamic_volumes = {}
        for idx, (vol_name, vol_config) in enumerate(dynamic_volume_lookup.items()):
            if vol_name == "dshm":
                logging.warning(f"Warning {vol_name} already in volume_mount dict!")
                continue
            dynamic_volumes.update(
                {
                    f"global.dynamicVolumes[{idx}].name": f"{vol_config["name"]}",
                    f"global.dynamicVolumes[{idx}].mount_path": f"{vol_config["mount_path"]}",
                }
            )

        # In case of debugging service_dag there is no self.project
        project_name = self.project.get("name") if self.project else "admin"
        ingress_path = (
            f"applications/project/{project_name}/release/" + "{{ .Release.Name }}"
        )
        

        helm_sets = {
            "global.complete_image": self.image,
            "global.namespace": self.namespace,
            "global.ingress_path": ingress_path,
            "global.display_name": self.display_name,
            **env_vars_sets,
            **dynamic_volumes,
            **env_vars_from_secret_key_refs,
            **dynamic_label_sets,
            **configmap_volume_config,
        }
        logging.info(helm_sets)
        # kaapanaint is there, so that it is recognized as a pending application!
        release_name = get_release_name(context)
        payload = {
            "name": "dev-server-chart",
            "version": KAAPANA_BUILD_VERSION,
            "release_name": release_name,
            "sets": helm_sets,
        }
        logging.info("payload")
        logging.info(payload)
        r = requests.post(url, json=payload)
        logging.info(r)
        logging.info(r.text)
        r.raise_for_status()
        t_end = time.time() + KaapanaBaseOperator.TIMEOUT
        while time.time() < t_end:
            time.sleep(15)
            url = f"{KaapanaBaseOperator.HELM_API}/view-chart-status"
            r = requests.get(url, params={"release_name": release_name})
            if r.status_code == 500 or r.status_code == 404:
                logging.info(
                    f"Release {release_name} was uninstalled. My job is done here!"
                )
                break
            r.raise_for_status()
        return

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
                    f"Processing container didn't finish in execution timeout: {self.execution_timeout.total_seconds()} seconds. The corresponding will be deleted!"
                )
            elif final_status == PodPhase.PENDING:
                raise AirflowException(
                    f"Processing container didn't start within {self.startup_timeout_seconds} seconds. The corresponding will be deleted!"
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

    @staticmethod
    def unique_task_identifer(context: Context):
        """
        Set a unique identifier for this task instance.

        :param context: Dictionary set by Airflow. It contains references to related objects to the task instance.
        """
        return f"{context["ti"].run_id}-{context["ti"].task_id}"

    @staticmethod
    def task_run_file_path(context: Context):
        """
        Return the path to the file, where the TaskInstance object will be stored.

        :param context: Dictionary set by Airflow. It contains references to related objects to the task instance.
        """
        unique_id = KaapanaBaseOperator.unique_task_identifer(context)
        return Path(AIRFLOW_WORKFLOW_DIR, context["run_id"], f"{unique_id}.pkl")

    # The order of this decorators matters because of the whitelist_federated_learning variable, do not change them!
    @cache_operator_output
    @federated_sharing_decorator
    def execute(self, context: Context):
        self.set_context_variables(context)
        if "gpu_device" in context["task_instance"].executor_config:
            self.env_vars.update(
                {
                    "CUDA_VISIBLE_DEVICES": str(
                        context["task_instance"].executor_config["gpu_device"]["gpu_id"]
                    )
                }
            )
        else:
            self.env_vars.update({"CUDA_VISIBLE_DEVICES": ""})

        if (
            context["dag_run"].conf is not None
            and "workflow_form" in context["dag_run"].conf
            and context["dag_run"].conf["workflow_form"] is not None
        ):
            workflow_form = context["dag_run"].conf["workflow_form"]
            logging.info(workflow_form)

            for key, value in workflow_form.items():
                key = key.upper()
                self.env_vars[key] = str(value)

        self.env_vars.update(
            {
                "RUN_ID": context["dag_run"].run_id,
                "DAG_ID": context["dag_run"].dag_id,
                "TASK_ID": context["task_instance"].task_id,
                "WORKFLOW_DIR": f"{PROCESSING_WORKFLOW_DIR}/{context['run_id']}",
                "BATCH_NAME": str(self.batch_name),
                "OPERATOR_OUT_DIR": str(self.operator_out_dir),
                "BATCHES_INPUT_DIR": f"{PROCESSING_WORKFLOW_DIR}/{context['run_id']}/{self.batch_name}",
            }
        )

        logging.info("CONTAINER ENVS:")
        logging.info(json.dumps(self.env_vars, indent=4, sort_keys=True))
        logging.info("CONTAINER ANNOTATIONS BEFORE RUN:")
        logging.info(json.dumps(self.annotations, indent=2, sort_keys=True))

        try:
            project_form = context.get("params").get("project_form")
            self.project = project_form
            self.namespace = project_form.get("kubernetes_namespace")
        except (KeyError, AttributeError):
            self.namespace = "project-admin"

        self.create_conf_configmap(context)

        self.set_volumes_and_volume_mounts()
        self.set_env_secrets()

        if self.dev_server == "code-server":
            return self.launch_dev_server(context)
        elif self.dev_server is not None:
            raise NameError("dev_server must be either None or code-server!")

        if self.delete_output_on_start is True:
            self.delete_operator_out_dir(context["run_id"], self.operator_out_dir)

        task_template = pc_models.TaskTemplate(
            identifier="main",
            description=f"This template is used for images that do not contain a processing-container.json file.",
            inputs=[],
            outputs=[],
            env=[],
        )

        self.task_run = KubernetesRunner.run(
            task=task_models.Task(
                name=KaapanaBaseOperator.unique_task_identifer(context),
                image=self.image,
                taskTemplate=task_template,
                inputs=[],
                outputs=[],
                resources=self.pod_resources,
                config=task_models.K8sConfig(
                    namespace=self.namespace,
                    imagePullSecrets=self.image_pull_secrets or ["registry-secret"],
                    env_vars=self.secrets
                    + [
                        client.V1EnvVar(name=key, value=val)
                        for key, val in self.env_vars.items()
                    ],
                    volumes=self.volumes,
                    volume_mounts=self.volume_mounts,
                    labels=self.labels,
                    annotations=self.annotations,
                ),
            )
        )
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        KubernetesRunner.dump(
            self.task_run, output=KaapanaBaseOperator.task_run_file_path(context)
        )
        self._monitor_task_run()

    def handle_sigterm(self, signum, frame):
        self.on_kill()
        raise AirflowException("Task was killed gracefully.")

    def on_kill(self):
        """
        Make sure that the corresponding pod is removed.
        """
        KubernetesRunner.stop(self.task_run)
        self.log.info("Pod deleted successfully!")

    def delete_operator_out_dir(self, run_id, operator_dir):
        logging.info(f"#### deleting {operator_dir} folders...!")
        run_dir = os.path.join(self.airflow_workflow_dir, run_id)
        batch_folders = sorted(
            [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]
        )
        for batch_element_dir in batch_folders:
            element_input_dir = os.path.join(batch_element_dir, operator_dir)
            logging.info(f"# Deleting: {element_input_dir} ...")
            shutil.rmtree(element_input_dir, ignore_errors=True)
        batch_input_dir = os.path.join(run_dir, operator_dir)
        logging.info(f"# Deleting: {batch_input_dir} ...")
        shutil.rmtree(batch_input_dir, ignore_errors=True)

    @staticmethod
    def stop_task_pod(context: Context):
        try:
            with open(KaapanaBaseOperator.task_run_file_path(context), "rb") as f:
                task_run = pickle.load(f)
                KubernetesRunner.stop(task_run=task_run)
            logging.info(f"Stopped processing-container: {task_run.id}")
        except FileNotFoundError:
            logging.info("Task File not found")
        except client.ApiException as e:
            logging.warning(f"Kubernetes API exception: {e}")
        finally:
            return None

    @staticmethod
    def on_failure(context: Context):
        """
        Use this method with caution, because it unclear at which state the context object is updated!
        """
        logging.info(
            "##################################################### ON FAILURE!"
        )
        KaapanaBaseOperator.stop_task_pod(context)

        release_name = get_release_name(context)
        url = f"{KaapanaBaseOperator.HELM_API}/view-chart-status"
        r = requests.get(url, params={"release_name": release_name})
        if r.status_code == 500 or r.status_code == 404:
            logging.info(
                f"Release {release_name} was uninstalled or never installed. My job is done here!"
            )
        else:
            from kaapana.operators.KaapanaApplicationOperator import (
                KaapanaApplicationOperator,
            )

            KaapanaApplicationOperator.uninstall_helm_chart(context)

        send_email_on_workflow_failure = context["dag_run"].dag.default_args.get(
            "send_email_on_workflow_failure", False
        )
        if send_email_on_workflow_failure:
            HelperSendEmailService.handle_task_failure_alert(context)

        send_notification_on_workflow_failure = context["dag_run"].dag.default_args.get(
            "send_notification_on_workflow_failure", False
        )
        if send_notification_on_workflow_failure:
            KaapanaBaseOperator.post_notification_to_user_from_context(context)

    @staticmethod
    def post_notification_to_user_from_context(context: Context):
        workflow_form = context["dag_run"].conf.get("workflow_form", {})
        username = workflow_form.get("username")
        if not username:
            # Assume it is a service dag
            user_ids = []
        else:
            # Get user ID
            user_resp = requests.get(
                f"{ServicesSettings().aii_url}/users/username/{username}"
            )
            user_resp.raise_for_status()
            user_id = user_resp.json()["id"]
            user_ids = [user_id]

        def fetch_default_project_id() -> str:
            response = requests.get(
                "http://aii-service.services.svc:8080/projects/admin"
            )
            response.raise_for_status()
            return response.json().get("id")

        project_form = context.get("params", {}).get("project_form", {})
        project_id = project_form.get("id", fetch_default_project_id())

        dag_id = context["dag_run"].dag_id
        run_id = context["dag_run"].run_id
        task_id = context["task_instance"].task_id

        notification = Notification(
            topic=run_id,
            title="Workflow failed",
            description=f"Workflow <b>{run_id}</b> failed.",
            icon="mdi-information",
            link=f"/flow/dags/{dag_id}/grid?dag_run_id={run_id}&task_id={task_id}&tab=logs",
        )

        return NotificationService.send(
            project_id=project_id, user_ids=user_ids, notification=notification
        )

    @staticmethod
    def on_success(context):
        """
        Use this method with caution, because it unclear at which state the context object is updated!
        """
        logging.info(
            "##################################################### on_success!"
        )

    @staticmethod
    def on_retry(context):
        """
        Use this method with caution, because it unclear at which state the context object is updated!
        """
        logging.info("##################################################### on_retry!")
        KaapanaBaseOperator.stop_task_pod(context)

    @staticmethod
    def on_execute(context):
        """
        Use this method with caution, because it unclear at which state the context object is updated!
        """
        pass

    def post_execute(self, context, result=None):
        logging.info(
            "##################################################### post_execute!"
        )
        logging.info(context)
        logging.info(result)

    def set_context_variables(self, context: Context):
        self.labels["run_id"] = cure_invalid_name(
            context["run_id"], r"(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?"
        )

    @staticmethod
    def set_defaults(
        obj,
        name,
        task_id,
        operator_out_dir,
        input_operator,
        operator_in_dir,
        parallel_id,
        keep_parallel_id,
        trigger_rule,
        pool,
        pool_slots,
        ram_mem_mb,
        ram_mem_mb_lmt,
        cpu_millicores,
        cpu_millicores_lmt,
        gpu_mem_mb,
        gpu_mem_mb_lmt,
        manage_cache,
        allow_federated_learning,
        whitelist_federated_learning,
        batch_name,
        airflow_workflow_dir,
        delete_input_on_success,
        delete_output_on_start,
        priority_class_name,
    ):
        obj.name = name

        obj.task_id = task_id
        obj.operator_out_dir = operator_out_dir
        obj.parallel_id = parallel_id

        obj.trigger_rule = trigger_rule
        obj.pool = pool
        obj.pool_slots = pool_slots
        obj.ram_mem_mb = ram_mem_mb
        obj.ram_mem_mb_lmt = ram_mem_mb_lmt
        obj.cpu_millicores = cpu_millicores
        obj.cpu_millicores_lmt = cpu_millicores_lmt
        obj.gpu_mem_mb = gpu_mem_mb if GPU_SUPPORT else None
        obj.gpu_mem_mb_lmt = gpu_mem_mb_lmt
        obj.manage_cache = manage_cache or "ignore"
        obj.allow_federated_learning = allow_federated_learning
        obj.whitelist_federated_learning = whitelist_federated_learning
        obj.delete_input_on_success = delete_input_on_success
        obj.delete_output_on_start = delete_output_on_start
        obj.priority_class_name = priority_class_name

        obj.batch_name = batch_name if batch_name != None else BATCH_NAME
        obj.airflow_workflow_dir = (
            airflow_workflow_dir
            if airflow_workflow_dir != None
            else AIRFLOW_WORKFLOW_DIR
        )

        if obj.task_id is None:
            obj.task_id = obj.name

        if (
            input_operator is not None
            and obj.parallel_id is None
            and input_operator.parallel_id is not None
            and keep_parallel_id
        ):
            obj.parallel_id = input_operator.parallel_id

        if obj.parallel_id is not None:
            obj.task_id = obj.task_id + "-" + obj.parallel_id.lower().replace(" ", "-")

        if obj.operator_out_dir is None:
            obj.operator_out_dir = obj.task_id

        if input_operator is not None and operator_in_dir is not None:
            raise NameError(
                "You need to define either input_operator or operator_in_dir!"
            )
        if input_operator is not None:
            obj.operator_in_dir = input_operator.operator_out_dir
        elif operator_in_dir is not None:
            obj.operator_in_dir = operator_in_dir

        if obj.allow_federated_learning is True:
            obj.delete_output_on_start = False

        enable_job_scheduler = (
            True
            if Variable.get("enable_job_scheduler", default_var="True").lower()
            == "true"
            else False
        )
        if obj.pool == None:
            if (
                not enable_job_scheduler
                and obj.gpu_mem_mb != None
                and obj.gpu_mem_mb != 0
            ):
                obj.pool = "NODE_GPU_COUNT"
                obj.pool_slots = 1
            else:
                obj.pool = "NODE_RAM"
                obj.pool_slots = obj.ram_mem_mb if obj.ram_mem_mb is not None else 1

        obj.executor_config = {
            "cpu_millicores": obj.cpu_millicores,
            "ram_mem_mb": obj.ram_mem_mb,
            "gpu_mem_mb": obj.gpu_mem_mb,
            "enable_job_scheduler": enable_job_scheduler,
        }

        return obj

    @staticmethod
    def extract_timestamp(s):
        """
        Accepts timestamp in the forms:
        - dcm2nifti-200831164505663620
        - manual__2020-08-31T16:58:05.469533+00:00
        if the format is not provided,the last 10 characters of the run_id will be added
        """

        run_id_identifier = None
        try:
            date_time_str = re.search(r"(.*)-(\d+)", s).group(2)
            date_time_obj = datetime.strptime(date_time_str, "%y%m%d%H%M%S%f")
            run_id_identifier = date_time_obj.strftime("%y%m%d%H%M%S%f")
        except (ValueError, AttributeError) as err:
            pass

        try:
            if s.startswith("manual__"):
                date_time_str = s[8:]
                date_time_obj = datetime.strptime(
                    date_time_str, "%Y-%m-%dT%H:%M:%S.%f+00:00"
                )
                run_id_identifier = date_time_obj.strftime("%y%m%d%H%M%S%f")
            else:
                pass
        except (ValueError, AttributeError) as err:
            pass

        if run_id_identifier is None:
            logging.info(
                "No timestamp found in run_id, the last 10 characters of the run_id will be taken as an identifier. When triggering a DAG externally please try to use the generate_run_id method!"
            )
            run_id_identifier = s[-10:]
        return run_id_identifier
