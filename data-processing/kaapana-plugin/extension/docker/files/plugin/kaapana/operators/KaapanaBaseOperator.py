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
from kaapana.kubetools import pod_launcher
from kaapana.kubetools.pod import Pod
from kaapana.kubetools.pod_stopper import PodStopper
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.kubetools.secret import Secret
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.operators import HelperSendEmailService
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperFederated import federated_sharing_decorator
from kaapanapy.services.NotificationService import Notification, NotificationService
from kaapanapy.settings import ServicesSettings

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

    pod_stopper = PodStopper()

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
        startup_timeout_seconds=120,
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
        self.labels.update({"pod-type": "processing-container"})
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
        self.extensions_namespace = os.getenv("EXTENSIONS_NAMESPACE", "")
        # self.helm_namespace = os.getenv("HELM_NAMESPACE", "")

        if self.pod_resources is None:
            pod_resources = PodResources(
                request_cpu=(
                    "{}m".format(self.cpu_millicores)
                    if self.cpu_millicores != None
                    else None
                ),
                limit_cpu=(
                    "{}m".format(self.cpu_millicores + 100)
                    if self.cpu_millicores != None
                    else None
                ),
                request_memory="{}Mi".format(self.ram_mem_mb),
                limit_memory="{}Mi".format(
                    self.ram_mem_mb_lmt
                    if self.ram_mem_mb_lmt is not None
                    else self.ram_mem_mb + 100
                ),
                limit_gpu=None,  # 1 if self.gpu_mem_mb is not None else None
            )
            self.pod_resources = pod_resources

        envs = {
            "SERVICES_NAMESPACE": str(self.services_namespace),
            "ADMIN_NAMESPACE": str(self.admin_namespace),
            "EXTENSIONS_NAMESPACE": str(self.extensions_namespace),
            # "HELM_NAMESPACE": str(self.helm_namespace),
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
                Volume(
                    name="workflowdata",
                    configs={
                        "PersistentVolumeClaim": {
                            "claim_name": f"{self.namespace}-workflow-data-pv-claim",
                            "read_only": False,
                        }
                    },
                ),
                VolumeMount(
                    "workflowdata",
                    mount_path=PROCESSING_WORKFLOW_DIR,
                    sub_path=None,
                    read_only=False,
                ),
            ),
            (
                Volume(
                    name="models",
                    configs={
                        "PersistentVolumeClaim": {
                            "claim_name": f"{self.namespace}-models-pv-claim",
                            "read_only": False,
                        }
                    },
                ),
                VolumeMount(
                    "models", mount_path="/models", sub_path=None, read_only=False
                ),
            ),
            (
                Volume(
                    name="mounted-scripts",
                    configs={
                        "PersistentVolumeClaim": {
                            "claim_name": f"{self.namespace}-mounted-scripts-pv-claim",
                            "read_only": False,
                        }
                    },
                ),
                VolumeMount(
                    "mounted-scripts",
                    mount_path="/kaapana/mounted/workflows/mounted_scripts",
                    sub_path=None,
                    read_only=False,
                ),
            ),
            (
                Volume(
                    name="tensorboard",
                    configs={
                        "PersistentVolumeClaim": {
                            "claim_name": f"{self.namespace}-tensorboard-pv-claim",
                            "read_only": False,
                        }
                    },
                ),
                VolumeMount(
                    "tensorboard",
                    mount_path="/tensorboard",
                    sub_path=None,
                    read_only=False,
                ),
            ),
            (
                Volume(name="dshm", configs={"emptyDir": {"medium": "Memory"}}),
                VolumeMount(
                    "dshm", mount_path="/dev/shm", sub_path=None, read_only=False
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
        project_credentials_password = Secret(
            deploy_type="env",
            deploy_target="KAAPANA_PROJECT_USER_PASSWORD",
            secret="project-user-credentials",
            key="project-user-password",
        )

        project_credentials_username = Secret(
            deploy_type="env",
            deploy_target="KAAPANA_PROJECT_USER_NAME",
            secret="project-user-credentials",
            key="project-user",
        )

        oidc_client_secret = Secret(
            deploy_type="env",
            deploy_target="KAAPANA_CLIENT_SECRET",
            secret="oidc-client-secret",
            key="oidc-client-secret",
        )

        self.secrets.extend(
            [
                project_credentials_password,
                project_credentials_username,
                oidc_client_secret,
            ]
        )

    def launch_dev_server(self, context):
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
                    f"global.envVarsFromSecretRef[{idx}].name": secret.deploy_target,
                    f"global.envVarsFromSecretRef[{idx}].secretName": secret.secret,
                    f"global.envVarsFromSecretRef[{idx}].secretKey": secret.key,
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

        volume_mounts_lookup = {}
        for volume_mount in self.volume_mounts:
            if (
                volume_mount.name in volume_mounts_lookup.values()
                or volume_mount.name == "dshm"
            ):
                logging.warning(
                    f"Warning {volume_mount.name} already in volume_mount dict!"
                )
                continue
            volume_mounts_lookup.update({volume_mount.name: volume_mount.mount_path})
        logging.info(volume_mounts_lookup)

        volume_claims_lookup = {}
        for volume in self.volumes:
            if "PersistentVolumeClaim" in volume.configs:
                if (
                    volume.name in volume_claims_lookup.values()
                    or volume.name == "dshm"
                ):
                    logging.warning(f"Warning {volume.name} already in volume dict!")
                    continue
                volume_claims_lookup.update(
                    {
                        volume.name: volume.configs["PersistentVolumeClaim"][
                            "claim_name"
                        ].replace("-pv-claim", "")
                    }
                )
        logging.info(volume_claims_lookup)

        dynamic_volumes = {}
        for idx, (k, name) in enumerate(volume_claims_lookup.items()):
            dynamic_volumes.update(
                {
                    f"global.dynamicVolumes[{idx}].name": f"{name}",
                    f"global.dynamicVolumes[{idx}].mount_path": f"{volume_mounts_lookup[k]}",
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

    # The order of this decorators matters because of the whitelist_federated_learning variable, do not change them!
    @cache_operator_output
    @federated_sharing_decorator
    def execute(self, context):
        config_path = os.path.join(
            self.airflow_workflow_dir, context["run_id"], "conf", "conf.json"
        )
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        if context["dag_run"].conf is not None:  # not os.path.isfile(config_path) and
            with open(os.path.join(config_path), "w") as file:
                json.dump(context["dag_run"].conf, file, indent=4, sort_keys=True)

        self.set_context_variables(context)
        # Same expression as in on_failure method!
        self.kube_name = cure_invalid_name(
            context["run_id"]
            .replace(context["dag_run"].dag_id, context["task_instance"].task_id)
            .replace("manual", context["task_instance"].task_id)
            .replace("scheduled", context["task_instance"].task_id),
            KaapanaBaseOperator.CURE_INVALID_NAME_REGEX,
            63,
        )  # actually 63, but because of helm set to 53, maybe...

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

        try:
            project_form = context.get("params").get("project_form")
            self.project = project_form
            self.namespace = project_form.get("kubernetes_namespace")
        except (KeyError, AttributeError):
            self.namespace = "project-admin"
        self.set_volumes_and_volume_mounts()
        self.set_env_secrets()

        if self.dev_server == "code-server":
            return self.launch_dev_server(context)
        elif self.dev_server is not None:
            raise NameError("dev_server must be either None or code-server!")

        if self.delete_output_on_start is True:
            self.delete_operator_out_dir(context["run_id"], self.operator_out_dir)

        try:
            logging.info("++++++++++++++++++++++++++++++++++++++++++++++++ launch pod!")
            logging.info(self.name)
            pod = Pod(
                image=self.image,
                name=self.kube_name,
                envs=self.env_vars,
                cmds=self.cmds,
                args=self.arguments,
                api_version=self.api_version,
                kind=self.kind,
                secrets=self.secrets,
                labels=self.labels,
                node_selectors=self.node_selectors,
                tolerations=self.tolerations,
                volumes=self.volumes,
                volume_mounts=self.volume_mounts,
                namespace=self.namespace,
                image_pull_policy=self.image_pull_policy,
                image_pull_secrets=self.image_pull_secrets,
                priority_class_name=self.priority_class_name,
                resources=self.pod_resources,
                annotations=self.annotations,
                affinity=self.affinity,
            )
            launcher = pod_launcher.PodLauncher(extract_xcom=self.xcom_push)

            launcher_return = launcher.run_pod(
                pod=pod,
                startup_timeout=self.startup_timeout_seconds,
                get_logs=self.get_logs,
            )
        except AirflowException as ex:
            raise AirflowException("Pod Launching failed: {error}".format(error=ex))

        if launcher_return is None:
            raise AirflowException("Problems launching the pod...")
        else:
            (result, message) = launcher_return
            self.result_message = result
            logging.info("RESULT: {}".format(result))
            logging.info("MESSAGE: {}".format(message))

            if result == State.SKIPPED:
                KaapanaBaseOperator.pod_stopper.stop_pod_by_name(
                    pod_id=self.kube_name, namespace=self.namespace
                )
                raise AirflowSkipException("Pod has been skipped!")
            elif result != State.SUCCESS:
                raise AirflowException("Pod returned a failure!")
            else:
                if self.delete_input_on_success:
                    self.delete_operator_out_dir(
                        context["run_id"], self.operator_in_dir
                    )
            if self.xcom_push:
                return result

    def on_kill(self) -> None:
        logging.info("##################################################### ON KILL!")
        KaapanaBaseOperator.pod_stopper.stop_pod_by_name(
            pod_id=self.kube_name, namespace=self.namespace
        )

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
    def on_failure(context):
        """
        Use this method with caution, because it unclear at which state the context object is updated!
        """
        logging.info(
            "##################################################### ON FAILURE!"
        )
        # Same expression as in execute method!
        kube_name = cure_invalid_name(
            context["run_id"]
            .replace(context["dag_run"].dag_id, context["task_instance"].task_id)
            .replace("manual", context["task_instance"].task_id)
            .replace("scheduled", context["task_instance"].task_id),
            KaapanaBaseOperator.CURE_INVALID_NAME_REGEX,
            63,
        )  # actually 63, but because of helm set to 53, maybe...
        time.sleep(2)  # since the phase needs some time to get updated
        try:
            project_form = context.get("params").get("project_form")
            namespace = project_form.get("kubernetes_namespace")
        except (KeyError, AttributeError):
            namespace = "project-admin"

        KaapanaBaseOperator.pod_stopper.stop_pod_by_name(
            pod_id=kube_name, namespace=namespace, phases=["Pending", "Running"]
        )
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
    def post_notification_to_user_from_context(context):
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
        project_id = project_form.get("name", fetch_default_project_id())

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

    def set_context_variables(self, context):
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
