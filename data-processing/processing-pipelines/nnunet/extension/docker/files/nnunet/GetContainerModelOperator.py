from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version
from datetime import timedelta
import os


class GetContainerModelOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=240)

    def pre_execute(self, context):
        print("++++++++++++++++++++++++++++ pre_execute operator")
        if context['dag_run'].conf is not None and "form_data" in context['dag_run'].conf and "task" in context['dag_run'].conf["form_data"]:
            form_data = context['dag_run'].conf["form_data"]
            self.model = form_data["model"] if "model" in form_data else "2d"
            self.task_id = form_data["task"]
        else:
            print("Could not find task in dagrun_conf!")
            print("Abort!")
            raise ValueError('ERROR')

        self.model_path = os.path.join(self.af_models_dir,"nnUNet", self.model, self.task_id)
        print("Check if model already present: {}".format(self.model_path))
        print("TASK: {}".format(self.task_id))
        print("MODEL: {}".format(self.model))
        if os.path.isdir(self.model_path):
            print("Model {} found!".format(self.task_id))
            self.skip_execute = True
        else:
            print("Model {} NOT found at {}!".format(self.task_id,self.model_path))
            self.skip_execute = False

        super().pre_execute(context)

    def execute(self, context):
        print("++++++++++++++++++++++++++++ execute operator")
        if not self.skip_execute:
            self.image = f"{self.registry_url}/model-nnunet-{self.task_id.lower().replace('_', '-')}:{self.model_version}"
            print("Pulling image: {}".format(self.image))
            super().execute(context)

    def post_execute(self, context, result):
        print("++++++++++++++++++++++++++++ post_execute operator")
        if not self.skip_execute:
            if not os.path.isdir(self.model_path):
                print("Model {} still not found after execution!".format(self.task_id))
                raise ValueError('ERROR')
        super().post_execute(context,result)

    def __init__(self,
                 dag,
                 env_vars={},
                 registry_url=None,
                 model_version=None,
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):

        self.registry_url = registry_url or default_registry
        self.model_version = model_version
        self.af_models_dir = "/models"
        
        host_models_dir = os.path.join(os.path.dirname(os.getenv('DATADIR', "")), "models")
        envs = {
            "MODELDIR": "/models_mount",
        }
        env_vars.update(envs)

        volume_mounts = []
        volumes = []

        volume_mounts.append(VolumeMount(
            'models', mount_path='/models_mount', sub_path=None, read_only=False))
        volume_config = {
            'hostPath':
            {
                'type': 'DirectoryOrCreate',
                'path': host_models_dir
            }
        }
        volumes.append(Volume(name='models', configs=volume_config))

        super().__init__(
            dag=dag,
            image=None,
            name="get-task-model",
            image_pull_secrets=["registry-secret"],
            volumes=volumes,
            volume_mounts=volume_mounts,
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=50,
            *args,
            **kwargs
        )
