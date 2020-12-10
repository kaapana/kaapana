from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta
import os
import json


class NnUnetOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(days=2)
    task_dict = {}

    def __init__(self,
                 dag,
                 mode,
                 processes_low=6,
                 processes_full=4,
                 folds=5,
                 modality_nifti_dirs=[],
                 modality_dicom_dirs=[],
                 train_config="nnUNetTrainerV2",
                 preprocess="true",
                 check_integrity="true",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):
        # Task042_LiverTest
        envs = {
            "INPUT_NIFTI_DIRS": ";".join(str(dir) for dir in modality_nifti_dirs),
            "INPUT_DICOM_DIRS": ";".join(str(dir) for dir in modality_dicom_dirs),
            "MODE": str(mode),
            "PREPROCESS": preprocess,
            "PL": str(processes_low),
            "PF": str(processes_full),
            "FOLDS": str(folds),
            "TRAIN_CONFIG": train_config,
            "CHECK_INTEGRITY": check_integrity,
            "TENSORBOARD_DIR": '/tensorboard',
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

        volume_mounts.append(VolumeMount(
            'dshm', mount_path='/dev/shm', sub_path=None, read_only=False))
        volume_config = {
            'emptyDir':
            {
                'medium': 'Memory',
            }
        }
        volumes.append(Volume(name='dshm', configs=volume_config))

        pod_resources = PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=1) if mode == "training" or mode == "inference" else None

        super().__init__(
            dag=dag,
            image="{}{}/nnunet:1.6.5-vdev".format(default_registry, default_project),
            name="nnunet",
            image_pull_secrets=["registry-secret"],
            volumes=volumes,
            volume_mounts=volume_mounts,
            execution_timeout=execution_timeout,
            ram_mem_mb=10000,
            ram_mem_mb_lmt=10000,
            gpu_mem_mb=None,
            pod_resources=pod_resources,
            env_vars=env_vars,
            *args,
            **kwargs
        )
