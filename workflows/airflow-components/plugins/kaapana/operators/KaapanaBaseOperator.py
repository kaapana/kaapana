import os
import glob
import re
import shutil
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
from kaapana.kubetools.resources import Resources as PodResources
from datetime import datetime, timedelta
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.dates import days_ago
from random import randint
from airflow.utils.operator_helpers import context_to_airflow_vars

from kaapana.blueprints.kaapana_utils import generate_run_id, cure_invalid_name
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperCaching import cache_operator_output
from airflow.api.common.experimental import pool as pool_api
import uuid
import json


default_registry = os.getenv("DEFAULT_REGISTRY", "")
default_project = os.getenv("DEFAULT_PROJECT", "")
http_proxy = os.getenv("PROXY", None)


class KaapanaBaseOperator(BaseOperator):
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
    pod_stopper = PodStopper()

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
                 task_concurrency=None,
                 manage_cache=None,
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
                 image_pull_policy=os.getenv('PULL_POLICY_PODS', 'IfNotPresent'),
                 training_operator=False,
                 volume_mounts=None,
                 volumes=None,
                 pod_resources=None,
                 enable_proxy=False,
                 host_network=False,
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
            batch_name=batch_name,
            workflow_dir=workflow_dir,
            delete_input_on_success=delete_input_on_success
        )

        # Airflow
        self.retries = retries
        self.priority_weight = priority_weight
        self.execution_timeout = execution_timeout
        self.task_concurrency = task_concurrency
        self.retry_delay = retry_delay

        self.training_operator = training_operator

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
        self.result_message = None
        self.host_network = host_network
        self.enable_proxy = enable_proxy

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

        if self.training_operator:
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
            "BATCHES_INPUT_DIR": f"/{self.workflow_dir}/{self.batch_name}"
        }
        if hasattr(self, 'operator_in_dir'):
            envs["OPERATOR_IN_DIR"] = str(self.operator_in_dir)

        if http_proxy is not None and http_proxy != "" and self.enable_proxy:
            envs.update(
                {
                    "http_proxy": http_proxy,
                    "https_proxy": http_proxy,
                    "HTTP_PROXY": http_proxy,
                    "HTTPS_PROXY": http_proxy,
                }
            )

        envs.update(self.env_vars)
        self.env_vars = envs
        super().__init__(
            dag=dag,
            task_id=self.task_id,
            retries=self.retries,
            priority_weight=self.priority_weight,
            execution_timeout=self.execution_timeout,
            task_concurrency=self.task_concurrency,
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

    @cache_operator_output
    def execute(self, context):
        self.set_context_variables(context)

        if self.parallel_id is None:
            self.kube_name = f'{self.name}'
        else:
            self.kube_name = f'{self.name}-{self.parallel_id}'

        self.kube_name = self.kube_name.lower() + "-" + str(uuid.uuid4())[:8]
        self.kube_name = cure_invalid_name(self.kube_name, r'[a-z]([-a-z0-9]*[a-z0-9])?', 63)

        self.pool = context["ti"].pool
        self.pool_slots = context["ti"].pool_slots
        if "GPU" in self.pool and len(self.pool.split("_")) == 3:
            gpu_id = self.pool.split("_")[1]
            self.env_vars.update({
                "CUDA_VISIBLE_DEVICES": str(gpu_id)
            })

        if context['dag_run'].conf is not None and "conf" in context['dag_run'].conf and "form_data" in context['dag_run'].conf["conf"] and context['dag_run'].conf["conf"]["form_data"] is not None:
            form_data = context['dag_run'].conf["conf"]["form_data"]
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
            print("CONTAINER ENVS:")
            print(json.dumps(self.env_vars, indent=4, sort_keys=True))

        for volume in self.volumes:
            if "hostPath" in volume.configs and self.data_dir == volume.configs["hostPath"]["path"]:
                volume.configs["hostPath"]["path"] = os.path.join(volume.configs["hostPath"]["path"], context["run_id"])

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
                host_network=self.host_network,
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
            data_dir = "/data"
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
            if obj.gpu_mem_mb != None:
                obj.pool = "GPU_COUNT"
                obj.pool_slots = obj.gpu_mem_mb
            else:
                obj.pool = "MEMORY"
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
