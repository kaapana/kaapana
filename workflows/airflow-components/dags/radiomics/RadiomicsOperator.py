from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from datetime import timedelta


class RadiomicsOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 mask_operator,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=120),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "MASK_OPERATOR_DIR": str(mask_operator.operator_out_dir),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="dktk-jip-registry.dkfz.de/processing-external/radiomics:1.0.1-vdev",
            name="radiomics",
            env_vars=env_vars,
            image_pull_secrets=["camic-registry"],
            execution_timeout=execution_timeout,
            task_concurrency=10,
            ram_mem_mb=3000,
            *args,
            **kwargs
            )
