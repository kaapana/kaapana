from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.kubetools.resources import Resources as PodResources
from datetime import timedelta


class MaskCtOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=60)

    def __init__(self,
                 dag,
                 threads=3,
                 env_vars=None,
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs):

        if env_vars is None:
            env_vars = {}

        envs = {
            "NUM_THREADS": str(threads),
        }
        env_vars.update(envs)

        pod_resources = None
        # pod_resources = PodResources(request_memory='5000Mi', request_cpu="1",limit_memory="7000Mi", limit_cpu="1", limit_gpu=None)

        super(MaskCtOperator, self).__init__(
            dag=dag,
            image="dktk-jip-registry.dkfz.de/ctpet/create-mask:0.4-vdev",
            name="create-mask",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            # manage_cache = "cache",
            pod_resources=pod_resources,
            env_vars=env_vars,
            ram_mem_mb=6000,
            ram_mem_mb_lmt=8000,
            gpu_mem_mb=None,
            *args,
            **kwargs)
