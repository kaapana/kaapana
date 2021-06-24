from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta
import os


class GetTaskModelOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=240)

    def __init__(self,
                 dag,
                 name="get-task-model",
                 task_id=None,
                 zip_file=False,
                 target_level="default",
                 operator_out_dir="/models",
                 mode="install_pretrained",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):

        envs = {
            "MODE": str(mode),
            "TARGET_LEVEL": str(target_level),
            "ZIP_FILE": str(zip_file)
        }
        env_vars.update(envs)

        if task_id is not None:
            env_vars["TASK"] = task_id

        data_dir = os.getenv('DATADIR', "")
        models_dir = os.path.join(os.path.dirname(data_dir), "models")

        volume_mounts = []
        volumes = []

        volume_mounts.append(VolumeMount(
            'models', mount_path='/models', sub_path=None, read_only=False))
        volume_config = {
            'hostPath':
            {
                'type': 'DirectoryOrCreate',
                'path': models_dir
            }
        }
        volumes.append(Volume(name='models', configs=volume_config))

        super().__init__(
            dag=dag,
            image=f"{default_registry}/nnunet-get-models:0.1.1-vdev",
            name=name,
            operator_out_dir=operator_out_dir,
            image_pull_secrets=["registry-secret"],
            volumes=volumes,
            volume_mounts=volume_mounts,
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            enable_proxy=True,
            host_network=True,
            ram_mem_mb=1000,
            *args,
            **kwargs
        )
