from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry
from datetime import timedelta


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
                 prep_min_combination=None,
                 train_fold=None,
                 model="3d_lowres",
                 train_network_trainer="nnUNetTrainerV2",
                 train_continue=False,
                 interpolation_order="default",
                 train_npz=False,
                 train_disable_post=True,
                 train_strict=True,
                 train_max_epochs=1000,
                 mixed_precision=True,
                 test_time_augmentation=False,
                 inf_batch_dataset=False,
                 inf_threads_prep=1,
                 inf_threads_nifti=1,
                 inf_softmax=False,
                 inf_seg_filter=None,
                 inf_remove_if_empty = True,
                 protocols = None,
                 body_part = None,
                 node_uid="N/A",
                 models_dir="/models",
                 env_vars={},
                 parallel_id=None,
                 execution_timeout=execution_timeout,
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
            "PRED_MIN_COMBINATION": str(prep_min_combination),
            "TRAIN_FOLD": str(train_fold),
            "MODEL": str(model),
            "PROTOCOLS": str(protocols),
            "BODY_PART": str(body_part),
            "TRAIN_NETWORK_TRAINER": str(train_network_trainer),
            "INTERPOLATION_ORDER": str(interpolation_order),
            "TRAIN_CONTINUE": str(train_continue),
            "TRAIN_MAX_EPOCHS": str(train_max_epochs),
            "TRAIN_NPZ": str(train_npz),
            "TRAIN_DISABLE_POSTPROCESSING": str(train_disable_post),
            "TRAIN_STRICT": str(train_strict),
            "TEST_TIME_AUGMENTATION": str(test_time_augmentation),
            "MIXED_PRECISION": str(mixed_precision),
            "INF_THREADS_PREP": str(inf_threads_prep),
            "INF_THREADS_NIFTI": str(inf_threads_nifti),
            "INF_BATCH_DATASET": str(inf_batch_dataset),
            "INF_SOFTMAX": str(inf_softmax),
            "INF_SEG_FILTER": str(inf_seg_filter),
            "INF_REMOVE_IF_EMPTY": str(inf_remove_if_empty),
            "NODE_UID": str(node_uid),
            "TENSORBOARD_DIR": '/tensorboard',
        }
        env_vars.update(envs)

        gpu_mem_mb = None
        pod_resources = PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=None)
        if mode == "training" or mode == "inference" or mode == "ensemble":
            if mode == "training":
                gpu_mem_mb = 11000
            elif mode == "inference" or mode == "ensemble":
                gpu_mem_mb = 5500

        parallel_id = parallel_id if parallel_id is not None else mode
        super().__init__(
            dag=dag,
            image=f"{default_registry}/nnunet:04-21",
            name="nnunet",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            allow_federated_learning=True,
            training_operator=True,
            # image_pull_policy="Always",
            ram_mem_mb=None,
            ram_mem_mb_lmt=None,
            pod_resources=pod_resources,
            gpu_mem_mb=gpu_mem_mb,
            env_vars=env_vars,
            **kwargs
        )
