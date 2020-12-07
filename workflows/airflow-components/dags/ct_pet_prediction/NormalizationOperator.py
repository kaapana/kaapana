from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from datetime import timedelta
class NormalizationOperator(KaapanaBaseOperator):

    execution_timeout = timedelta(minutes=60)

    def __init__(self,
                 dag,
                 resampling_operator,
                 mask_operator,
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
            "RESAMPLING_OPERATOR_DIR": resampling_operator.operator_out_dir,
            "MASK_OPERATOR_DIR": mask_operator.operator_out_dir 
        }
        env_vars.update(envs)
        # pod_resources = PodResources(request_memory='2000Mi', request_cpu="1",limit_memory="5000Mi", limit_cpu="1", limit_gpu=None)
        pod_resources = None

        super(NormalizationOperator, self).__init__(
            dag=dag,
            image="dktk-jip-registry.dkfz.de/ctpet/normalization:0.4-vdev",
            name="normalization",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            pod_resources=pod_resources,
            env_vars=env_vars,
            ram_mem_mb=10000,
            ram_mem_mb_lmt=12000,
            gpu_mem_mb=None,
            *args,
            **kwargs)
