from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta
import os
import json


class NnUnetOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=120)
    task_dict = {}

    def __init__(self,
                 dag,
                 env_vars={},
                 input_dirs=[],
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):

        envs = {
            "INPUT_DIRS": ";".join(str(dir) for dir in input_dirs),
            "nnUNet_raw_data_base": "/input",
            "nnUNet_preprocessed": "/input/nnUNet_preprocessed",
            "RESULTS_FOLDER": "/models",
        }
        env_vars.update(envs)

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

        super(NnUnetOperator, self).__init__(
            dag=dag,
            image="{}{}/nnunet-predict:0.2-vdev".format(default_registry, default_project),
            name="nnunet-predict",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            volumes=volumes,
            volume_mounts=volume_mounts,
            execution_timeout=execution_timeout,
            ram_mem_mb=15000,
            gpu_mem_mb=4500,
            env_vars=env_vars,
            *args,
            **kwargs
        )
