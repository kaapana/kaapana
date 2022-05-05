import os
import glob
import re
import shutil
import requests
import time
from datetime import datetime
from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.utils.state import State
from kaapana.kubetools import kube_client, pod_launcher
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.pod import Pod
from kaapana.kubetools.pod_stopper import PodStopper
from airflow.models.skipmixin import SkipMixin
from kaapana.kubetools.resources import Resources as PodResources
from datetime import datetime, timedelta
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.dates import days_ago
from random import randint
from airflow.utils.operator_helpers import context_to_airflow_vars

from kaapana.blueprints.kaapana_utils import generate_run_id, cure_invalid_name
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperFederated import federated_sharing_decorator
import uuid
import json
import logging
from airflow.models import Variable

default_registry = os.getenv("DEFAULT_REGISTRY", "")
default_project = os.getenv("DEFAULT_PROJECT", "")
default_proxy = os.getenv("PROXY", "")

class KaapanaBaseOperator(BaseOperator, SkipMixin):
    """
    Execute a task in a Kubernetes Pod

    :param image: Docker image you wish to launch. Defaults to dockerhub.io,
        but fully qualified URLS will point to custom repositories
    :type image: str
    :param: namespace: the namespace to run within kubernetes
    :type: namespace: str
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
    :param config_file: The path to the Kublernetes config file
    :type config_file: str
    :param xcom_push: If xcom_push is True, the content of the file
        /airflow/xcom/return.json in the container will also be pushed to an
        XCom when the container completes.
    :type xcom_push: bool
    """

    HELM_API = 'http://kube-helm-service.kube-system.svc:5000'
    TIMEOUT = 60 * 60 * 12

    pod_stopper = PodStopper()
    env_pull_policy = os.getenv('PULL_POLICY_PODS',"None")

    @apply_defaults
    def __init__(self,
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
                 priority_weight=1,
                 execution_timeout=timedelta(minutes=90),
                 max_active_tis_per_dag=None,
                 manage_cache=None,
                 allow_federated_learning=False,
                 whitelist_federated_learning=None,
                 delete_input_on_success=False,
                 # Other stuff
                 batch_name=None,
                 workflow_dir=None,
                 cmds=None,
                 arguments=None,
                 env_vars=None,
                 image_pull_secrets=None,
                 startup_timeout_seconds=120,
                 namespace='flow-jobs',
                 image_pull_policy= env_pull_policy if env_pull_policy == env_pull_policy.lower() == "never" else 'IfNotPresent',
                 volume_mounts=None,
                 volumes=None,
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
                 secrets=None,
                 kind="Pod",
                 pool=None,
                 pool_slots=None,
                 api_version="v1",
                 dev_server=None,
                 **kwargs
                 ):

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
            workflow_dir=workflow_dir,
            delete_input_on_success=delete_input_on_success
        )

        # Airflow
        self.retries = retries
        self.priority_weight = priority_weight
        self.execution_timeout = execution_timeout
        self.max_active_tis_per_dag = max_active_tis_per_dag
        self.retry_delay = retry_delay

        # helm
        if dev_server not in [None, 'code-server', 'jupyterlab']:
            raise NameError('dev_server must be either None, code-server or jupyterlab!')
        if dev_server is not None:
            self.execution_timeout = None
        self.dev_server = dev_server

        # Kubernetes
        self.image = image
        self.env_vars = env_vars or {}
        self.namespace = namespace
        self.cmds = cmds or []
        self.arguments = arguments or []
        self.labels = labels or {}
        self.startup_timeout_seconds = startup_timeout_seconds
        self.volume_mounts = volume_mounts or []
        self.volumes = volumes or []
        self.image_pull_secrets = image_pull_secrets or []
        self.in_cluster = in_cluster
        self.cluster_context = cluster_context
        self.get_logs = get_logs
        self.image_pull_policy = image_pull_policy
        self.node_selectors = node_selectors or {}
        self.annotations = annotations or {}
        self.affinity = affinity or {}
        self.xcom_push = xcom_push
        self.pod_resources = pod_resources or None
        self.config_file = config_file
        self.api_version = api_version
        self.secrets = secrets
        self.kind = kind
        self.data_dir = os.getenv('DATADIR', "")
        self.model_dir = os.getenv('MODELDIR', "")
        self.common_dir = os.getenv('COMMONDIR', "")
        self.result_message = None

        self.volume_mounts.append(VolumeMount(
            'workflowdata', mount_path='/data', sub_path=None, read_only=False
        ))

        self.volumes.append(
            Volume(name='workflowdata', configs={'hostPath':
                                                 {
                                                     'type': 'DirectoryOrCreate',
                                                     'path': self.data_dir
                                                 }
                                                 })
        )
        self.volume_mounts.append(VolumeMount(
            'miniodata', mount_path='/minio', sub_path=None, read_only=False
        ))
        self.volume_mounts.append(VolumeMount(
            'commondata', mount_path='/common', sub_path=None, read_only=False
        ))

        self.volumes.append(
            Volume(name='miniodata', configs={
                'hostPath':
                {
                    'type': 'DirectoryOrCreate',
                    'path': os.getenv('MINIODIR', "/home/kaapana/minio")
                }
            })
        )

        self.volumes.append(
            Volume(name='commondata', configs={
                'hostPath':
                {
                    'type': 'DirectoryOrCreate',
                    'path': self.common_dir
                }
            })
        )
        
        if self.gpu_mem_mb != None or self.gpu_mem_mb_lmt != None:
            self.volume_mounts.append(VolumeMount(
                'modeldata', mount_path='/models', sub_path=None, read_only=False
            ))

            self.volumes.append(
                Volume(name='modeldata', configs={'hostPath':
                                                  {
                                                      'type': 'DirectoryOrCreate',
                                                      'path': self.model_dir
                                                  }
                                                  })
            )

            self.volume_mounts.append(VolumeMount(
                'tensorboard', mount_path='/tensorboard', sub_path=None, read_only=False))
            tb_config = {
                'hostPath':
                {
                    'type': 'DirectoryOrCreate',
                    'path': os.path.join(self.data_dir, "tensorboard")
                }
            }
            self.volumes.append(Volume(name='tensorboard', configs=tb_config))

            self.volume_mounts.append(VolumeMount(
                'dshm', mount_path='/dev/shm', sub_path=None, read_only=False))
            volume_config = {
                'emptyDir':
                {
                    'medium': 'Memory',
                }
            }
            self.volumes.append(Volume(name='dshm', configs=volume_config))

        if self.pod_resources is None:
            pod_resources = PodResources(
                request_cpu="{}m".format(self.cpu_millicores) if self.cpu_millicores != None else None,
                limit_cpu="{}m".format(self.cpu_millicores+100) if self.cpu_millicores != None else None,
                request_memory="{}Mi".format(self.ram_mem_mb),
                limit_memory="{}Mi".format(self.ram_mem_mb_lmt if self.ram_mem_mb_lmt is not None else self.ram_mem_mb+100),
                limit_gpu=None  # 1 if self.gpu_mem_mb is not None else None
            )
            self.pod_resources = pod_resources

        envs = {
            "WORKFLOW_DIR": str(self.workflow_dir),
            "BATCH_NAME": str(self.batch_name),
            "OPERATOR_OUT_DIR": str(self.operator_out_dir),
            "BATCHES_INPUT_DIR": f"/{self.workflow_dir}/{self.batch_name}",
        }
        if default_proxy:
            envs.update({"PROXY": default_proxy})

        if hasattr(self, 'operator_in_dir'):
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
            email_on_retry=True,
            email_on_failure=True,
            start_date=days_ago(0),
            depends_on_past=False,
            wait_for_downstream=False,
            trigger_rule=self.trigger_rule,
            on_failure_callback=KaapanaBaseOperator.on_failure,
            on_success_callback=KaapanaBaseOperator.on_success,
            on_retry_callback=KaapanaBaseOperator.on_retry,
            on_execute_callback=KaapanaBaseOperator.on_execute,
            executor_config=self.executor_config,
            **kwargs
        )

    def clear(self, start_date=None, end_date=None, upstream=False, downstream=False, session=None):
        self.log.warning("##################################################### IN CLEAR!")
        self.log.warning(self)
        self.log.warning(self.ti)
        self.log.warning(self.ti.kube_name)

        super.clear(start_date=start_date, end_date=end_date, upstream=upstream, downstream=downstream, session=session)

    def rest_env_vars_update(self, payload):
        operator_conf = {}
        if 'global' in payload:
            operator_conf.update(payload['global'])
        if 'operators' in payload and self.name in payload['operators']:
            operator_conf.update(payload['operators'][self.name])

        for k, v in operator_conf.items():
            k = k.upper()
            self.env_vars[k] = str(v)

    # The order of this decorators matters because of the whitelist_federated_learning variable, do not change them!
    @cache_operator_output
    @federated_sharing_decorator
    def execute(self, context):

        config_path = os.path.join(self.workflow_dir, context["run_id"], 'conf', 'conf.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        if context['dag_run'].conf is not None: #not os.path.isfile(config_path) and
            with open(os.path.join(config_path), "w") as file:
                json.dump(context['dag_run'].conf, file)

        self.set_context_variables(context)

        if self.parallel_id is None:
            self.kube_name = f'{self.name}'
        else:
            self.kube_name = f'{self.name}-{self.parallel_id}'

        self.kube_name = self.kube_name.lower() + "-" + str(uuid.uuid4())[:8]
        self.kube_name = cure_invalid_name(self.kube_name, r'[a-z]([-a-z0-9]*[a-z0-9])?', 63) # actually 63, but because of helm set to 53, maybe...

        if "NODE_GPU_" in self.pool and self.pool.count("_") == 3:
            gpu_id = self.pool.split("_")[2]
            self.env_vars.update({
                "CUDA_VISIBLE_DEVICES": str(gpu_id)
            })

        # if context['dag_run'].conf is not None and "conf" in context['dag_run'].conf and "form_data" in context['dag_run'].conf["conf"] and context['dag_run'].conf["conf"]["form_data"] is not None:
        if context['dag_run'].conf is not None and "form_data" in context['dag_run'].conf and context['dag_run'].conf["form_data"] is not None:
            form_data = context['dag_run'].conf["form_data"]
            print(form_data)
            # form_envs = {}
            # for form_key in form_data.keys():
            #     form_envs[str(form_key.upper())] = str(form_data[form_key])

            # self.env_vars.update(form_envs)
            # print("CONTAINER ENVS:")
            # print(json.dumps(self.env_vars, indent=4, sort_keys=True))
            context['dag_run'].conf["rest_call"] = {'global': form_data}
        if context['dag_run'].conf is not None and "rest_call" in context['dag_run'].conf and context['dag_run'].conf["rest_call"] is not None:
            self.rest_env_vars_update(context['dag_run'].conf["rest_call"])

        self.env_vars.update({
            "RUN_ID": context["dag_run"].run_id,
            "DAG_ID": context["dag_run"].dag_id
        })

        print("CONTAINER ENVS:")
        print(json.dumps(self.env_vars, indent=4, sort_keys=True))

        for volume in self.volumes:
            if "hostPath" in volume.configs and self.data_dir == volume.configs["hostPath"]["path"]:
                volume.configs["hostPath"]["path"] = os.path.join(volume.configs["hostPath"]["path"], context["run_id"])

        if self.dev_server is not None:
            url = f'{KaapanaBaseOperator.HELM_API}/helm-install-chart'
            env_vars_sets = {}
            for idx, (k, v) in enumerate(self.env_vars.items()):
                env_vars_sets.update({
                    f'envVars[{idx}].name': f"{k}",
                    f'envVars[{idx}].value': f"{v}"
                })

            volume_mounts_sets = {}
            idx = 0
            for volume_mount in self.volume_mounts:
                print('vm name', volume_mount.name)
                print('vm mount_path', volume_mount.mount_path)
                if volume_mount.name in volume_mounts_sets.values() or volume_mount.name == 'dshm':
                    print(f'Warning {volume_mount.name} already in volume_mount dict!')
                    continue
                volume_mounts_sets.update({
                    f'volumeMounts[{idx}].name': f"{volume_mount.name}",
                    f'volumeMounts[{idx}].mountPath': f"{volume_mount.mount_path}"
                })
                idx = idx + 1
            print(volume_mounts_sets)
            volumes_sets = {}
            idx = 0
            for volume in self.volumes:
                if 'hostPath' in volume.configs:
                    print('v name', volume.name)
                    print('v path', volume.configs['hostPath']['path'])
                    if volume.name in volumes_sets.values() or volume.name == 'dshm':
                        print(f'Warning {volume.name} already in volume dict!')
                        continue
                    volumes_sets.update({
                        f'volumes[{idx}].name': f"{volume.name}",
                        f'volumes[{idx}].path': f"{volume.configs['hostPath']['path']}"
                    })
                    idx = idx + 1
            print(volumes_sets)

            helm_sets = {
                'image': self.image,
                **env_vars_sets,
                **volume_mounts_sets,
                **volumes_sets}
            print(helm_sets)
            # kaapanaint is there, so that it is recognized as a pending application!
            release_name = cure_invalid_name(f'kaapanaint-{self.kube_name}', r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", max_length=53)
            if self.dev_server == 'code-server':
                payload = {
                    'name': 'code-server-chart',
                    'version': '4.2.0',
                    'release_name': release_name,
                    'sets': helm_sets
                }
            elif self.dev_server == 'jupyterlab':
                payload = {
                    'name': 'jupyterlab-chart',
                    'version': '3.3.2',
                    'release_name': release_name,
                    'sets': helm_sets
                }
            else:
                raise NameError('dev_server must be either None, code-server or jupyterlab!')
            print('payload')
            print(payload)
            r = requests.post(url, json=payload)
            print(r)
            print(r.text)
            r.raise_for_status()
            t_end = time.time() + KaapanaBaseOperator.TIMEOUT
            while time.time() < t_end:
                time.sleep(15)
                url = f'{KaapanaBaseOperator.HELM_API}/view-chart-status'
                r = requests.get(url, params={'release_name': release_name})
                if r.status_code == 500:
                    print(f'Release {release_name} was uninstalled. My job is done here!')
                    break
                r.raise_for_status()
            return 
                
        try:
            print("++++++++++++++++++++++++++++++++++++++++++++++++ launch pod!")
            print(self.name)
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
                volumes=self.volumes,
                volume_mounts=self.volume_mounts,
                namespace=self.namespace,
                image_pull_policy=self.image_pull_policy,
                image_pull_secrets=self.image_pull_secrets,
                resources=self.pod_resources,
                annotations=self.annotations,
                affinity=self.affinity
            )
            launcher = pod_launcher.PodLauncher(extract_xcom=self.xcom_push)

            (result, message) = launcher.run_pod(
                pod=pod,
                startup_timeout=self.startup_timeout_seconds,
                get_logs=self.get_logs
            )
            self.result_message = result
            print("RESULT: {}".format(result))
            print("MESSAGE: {}".format(message))

            if result != State.SUCCESS:
                raise AirflowException('Pod returned a failure: {state}'.format(state=message))

            if self.xcom_push:
                return result
        except AirflowException as ex:
            raise AirflowException('Pod Launching failed: {error}'.format(error=ex))

    @staticmethod
    def on_failure(info_dict):
        print("##################################################### ON FAILURE!")
        print("## POD: {}".format(info_dict["ti"].task.kube_name))
        keep_pod_messages = [
            State.SUCCESS,
            State.FAILED
        ]
        result_message = info_dict["ti"].task.result_message
        if result_message not in keep_pod_messages:
            print("RESULT_MESSAGE: {}".format(result_message))
            print("--> delete pod!")
            pod_id = info_dict["ti"].task.kube_name
            KaapanaBaseOperator.pod_stopper.stop_pod_by_name(pod_id=pod_id)

    @staticmethod
    def on_success(info_dict):
        print("##################################################### on_success!")
        ti = info_dict["ti"].task
        if ti.delete_input_on_success:
            print("#### deleting input-dirs...!")
            data_dir  = os.path.join(WORKFLOW_DIR, info_dict['run_id'])
            batch_folders = sorted([f for f in glob.glob(os.path.join(data_dir, 'batch', '*'))])
            for batch_element_dir in batch_folders:
                element_input_dir = os.path.join(batch_element_dir, ti.operator_in_dir)
                print(f"# Deleting: {element_input_dir} ...")
                shutil.rmtree(element_input_dir, ignore_errors=True)

            batch_input_dir = os.path.join(data_dir, ti.operator_in_dir)
            print(f"# Deleting: {batch_input_dir} ...")
            shutil.rmtree(batch_input_dir, ignore_errors=True)

    @staticmethod
    def on_retry(info_dict):
        print("##################################################### on_retry!")
        print("## POD: {}".format(info_dict["ti"].task.kube_name))
        keep_pod_messages = [
            State.SUCCESS,
            State.FAILED
        ]
        result_message = info_dict["ti"].task.result_message
        if result_message not in keep_pod_messages:
            print("RESULT_MESSAGE: {}".format(result_message))
            print("--> delete pod!")
            pod_id = info_dict["ti"].task.kube_name
            KaapanaBaseOperator.pod_stopper.stop_pod_by_name(pod_id=pod_id)

    @staticmethod
    def on_execute(info_dict):
        pass

    def post_execute(self, context, result=None):
        print("##################################################### post_execute!")
        print(context)
        print(result)

    def set_context_variables(self, context):
        self.labels['run_id'] = cure_invalid_name(context["run_id"], r'(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')

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
        workflow_dir,
        delete_input_on_success
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
        obj.gpu_mem_mb = gpu_mem_mb
        obj.gpu_mem_mb_lmt = gpu_mem_mb_lmt
        obj.manage_cache = manage_cache or 'ignore'
        obj.allow_federated_learning = allow_federated_learning
        obj.whitelist_federated_learning = whitelist_federated_learning
        obj.delete_input_on_success = delete_input_on_success

        obj.batch_name = batch_name if batch_name != None else BATCH_NAME
        obj.workflow_dir = workflow_dir if workflow_dir != None else WORKFLOW_DIR

        if obj.task_id is None:
            obj.task_id = obj.name

        if input_operator is not None and obj.parallel_id is None and input_operator.parallel_id is not None and keep_parallel_id:
            obj.parallel_id = input_operator.parallel_id

        if obj.parallel_id is not None:
            obj.task_id = obj.task_id + "-" + obj.parallel_id.lower().replace(" ", "-")

        if obj.operator_out_dir is None:
            obj.operator_out_dir = obj.task_id

        if input_operator is not None and operator_in_dir is not None:
            raise NameError('You need to define either input_operator or operator_in_dir!')
        if input_operator is not None:
            obj.operator_in_dir = input_operator.operator_out_dir
        elif operator_in_dir is not None:
            obj.operator_in_dir = operator_in_dir

        if obj.pool == None:
            enable_job_scheduler = True if Variable.get("enable_job_scheduler", default_var="True").lower() == "true" else False
            if enable_job_scheduler and obj.gpu_mem_mb != None and obj.gpu_mem_mb != 0:
                obj.pool = "NODE_GPU_COUNT"
                obj.pool_slots = 1
            else:
                obj.pool = "NODE_RAM"
                obj.pool_slots = obj.ram_mem_mb if obj.ram_mem_mb is not None else 1

        obj.executor_config = {
            "cpu_millicores": obj.cpu_millicores,
            "ram_mem_mb": obj.ram_mem_mb,
            "gpu_mem_mb": obj.gpu_mem_mb
        }

        return obj

    @staticmethod
    def extract_timestamp(s):
        '''
        Accepts timestamp in the forms:
        - dcm2nifti-200831164505663620
        - manual__2020-08-31T16:58:05.469533+00:00
        if the format is not provided,the last 10 characters of the run_id will be added
        '''

        run_id_identifier = None
        try:
            date_time_str = re.search(r"(.*)-(\d+)", s).group(2)
            date_time_obj = datetime.strptime(date_time_str, '%y%m%d%H%M%S%f')
            run_id_identifier = date_time_obj.strftime('%y%m%d%H%M%S%f')
        except (ValueError, AttributeError) as err:
            pass

        try:
            if s.startswith('manual__'):
                date_time_str = s[8:]
                date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M:%S.%f+00:00')
                run_id_identifier = date_time_obj.strftime('%y%m%d%H%M%S%f')
            else:
                pass
        except (ValueError, AttributeError) as err:
            pass

        if run_id_identifier is None:
            print('No timestamp found in run_id, the last 10 characters of the run_id will be taken as an identifier. When triggering a DAG externally please try to use the generate_run_id method!')
            run_id_identifier = s[-10:]
        return run_id_identifier
