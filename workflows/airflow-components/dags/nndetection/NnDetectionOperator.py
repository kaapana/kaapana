from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry
from datetime import timedelta


class NnDetectionOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(days=10)
    task_dict = {}

    def __init__(self,
                 dag,
                 mode,  # preprocess, training, inference,export-model,install-model
                 input_modality_operators=[],
                 inf_batch_dataset=False,
                 inf_threads_prep=1,
                 inf_threads_nifti=1,
                 inf_softmax=False,
                 inf_seg_filter=None,
                 inf_remove_if_empty = True,
                 node_uid="N/A",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):
        envs = {
            "MODE": str(mode),
            "INPUT_MODALITY_DIRS": ",".join(str(operator.operator_out_dir) for operator in input_modality_operators),
            "INF_THREADS_PREP": str(inf_threads_prep),
            "INF_THREADS_NIFTI": str(inf_threads_nifti),
            "INF_BATCH_DATASET": str(inf_batch_dataset),
            "INF_SOFTMAX": str(inf_softmax),
            "INF_SEG_FILTER": str(inf_seg_filter),
            "INF_REMOVE_IF_EMPTY": str(inf_remove_if_empty),
            "NODE_UID": str(node_uid),
        }
        env_vars.update(envs)

        pod_resources = PodResources(request_memory=None, request_cpu=None, limit_memory=None, limit_cpu=None, limit_gpu=None)
        super().__init__(
            dag=dag,
            image=f"{default_registry}/nndetection_komorbidom:0.0.1",
            name="nnDetection",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            image_pull_policy="Always",
            ram_mem_mb=None,
            ram_mem_mb_lmt=None,
            pod_resources=pod_resources,
            gpu_mem_mb=7000,
            env_vars=env_vars,
            *args,
            **kwargs
        )
