from kaapana.kubetools.resources import Resources as PodResources
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta

class BprOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(minutes=10)
    task_dict = {}

    def __init__(self,
                 dag,
                 stringify_json=False,
                 env_vars={},
                 parallel_id=None,
                 execution_timeout=execution_timeout,
                 **kwargs
                 ):
        envs = { "STRINGIFY_JSON": str(stringify_json)}
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/bodypartregression:v1.3".format(default_registry, default_project),
            name="bodypartregression",
            parallel_id=parallel_id,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=3000,
            ram_mem_mb_lmt=6000,
            training_operator=False,
            gpu_mem_mb=None,
            env_vars=env_vars,
            **kwargs
        ) 
