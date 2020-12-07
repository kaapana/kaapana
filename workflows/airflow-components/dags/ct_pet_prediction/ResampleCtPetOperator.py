from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from datetime import timedelta
class ResampleCtPetOperator(KaapanaBaseOperator):

    execution_timeout = timedelta(minutes=320)

    def __init__(self,
                 dag,
                 ct_nifti_operator,
                 pet_nifti_operator,
                 threads=4,
                 env_vars=None,
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs):

        if env_vars is None:
            env_vars = {}

        envs = {
            "NUM_THREADS": str(threads),
            "CT_NII_OPERATOR_DIR": ct_nifti_operator.operator_out_dir,
            "PET_NII_OPERATOR_DIR": pet_nifti_operator.operator_out_dir
        }
        env_vars.update(envs)
        pod_resources = PodResources(request_memory='2500Mi', request_cpu="1",limit_memory="3000Mi", limit_cpu="1", limit_gpu=None)

        super(ResampleCtPetOperator, self).__init__(
            dag=dag,
            image="dktk-jip-registry.dkfz.de/ctpet/resample-ct-pet:0.4-vdev",
            name="resample-ct-pet",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            pod_resources=pod_resources,
            env_vars=env_vars,
            ram_mem_mb=1500,
            ram_mem_mb_lmt=3000,
            gpu_mem_mb=None,
            *args,
            **kwargs)
