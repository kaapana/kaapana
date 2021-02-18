from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta
import os
import json


class NnUnetOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(days=5)
    task_dict = {}

    def __init__(self,
                 dag,
                 mode,  # preprocess, training, inference,export-model,install-model
                 input_modality_operators=[],
                 prep_processes_low=8,
                 prep_processes_full=6,
                 prep_label_operators=[],
                 prep_modalities=[],
                 prep_preprocess=True,
                 prep_check_integrity=True,
                 prep_use_nifti_labels=True,
                 prep_copy_data=False,
                 prep_exit_on_issue=True,
                 train_fold="all",
                 train_network="3d_lowres",
                 train_network_trainer="nnUNetTrainerV2",
                 train_continue=False,
                 train_npz=False,
                 train_strict=True,
                 train_max_epochs=1000,
                 inf_preparation=True,
                 inf_threads_prep=1,
                 inf_threads_nifti=1,
                 inf_softmax=False,
                 models_dir="/models",
                 env_vars={},
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):
        envs = {
            "MODE": str(mode),
            "MODELS_DIR": str(models_dir),
            "INPUT_MODALITY_DIRS": ",".join(str(operator.operator_out_dir) for operator in input_modality_operators),
            "PREP_TL": str(prep_processes_low),
            "PREP_TF": str(prep_processes_full),
            "PREP_LABEL_DIRS": ",".join(str(operator.operator_out_dir) for operator in prep_label_operators),
            "PREP_MODALITIES": ",".join(str(modality) for modality in prep_modalities),
            "PREP_PREPROCESS": str(prep_preprocess),
            "PREP_CHECK_INTEGRITY": str(prep_check_integrity),
            "PREP_USE_NIFITI_LABELS": str(prep_use_nifti_labels),
            "PREP_EXIT_ON_ISSUE": str(prep_exit_on_issue),
            "PREP_COPY_DATA": str(prep_copy_data),
            "TRAIN_FOLD": str(train_fold),
            "TRAIN_NETWORK": train_network,
            "TRAIN_NETWORK_TRAINER": train_network_trainer,
            "TRAIN_CONTINUE": str(train_continue),
            "TRAIN_MAX_EPOCHS": str(train_max_epochs),
            "TRAIN_NPZ": str(train_npz),
            "TRAIN_STRICT": str(train_strict),
            "INF_THREADS_PREP": str(inf_threads_prep),
            "INF_THREADS_NIFTI": str(inf_threads_nifti),
            "INF_PREPARATION": str(inf_preparation),
            "INF_SOFTMAX": str(inf_softmax),
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

        pod_resources = PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=None)

        training_operator = False
        gpu_mem_mb = None

        if mode == "training" or mode == "inference":
            pod_resources = PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=1)
            gpu_mem_mb = 6000
            if mode == "training":
                gpu_mem_mb = None
                training_operator = True

        parallel_id = parallel_id if parallel_id is not None else mode

        super().__init__(
            dag=dag,
            image="{}{}/nnunet:1.6.5-vdev".format(default_registry, default_project),
            name="nnunet",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            volumes=volumes,
            volume_mounts=volume_mounts,
            execution_timeout=execution_timeout,
            ram_mem_mb=None,
            ram_mem_mb_lmt=None,
            pod_resources=pod_resources,
            training_operator=training_operator,
            gpu_mem_mb=gpu_mem_mb,
            env_vars=env_vars,
            *args,
            **kwargs
        )
