from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION
from datetime import timedelta

class RadiomicsOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 mask_operator,
                 parameters = "--all-features",
                 env_vars=None,
                 execution_timeout=timedelta(minutes=120),
                 **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "MASK_OPERATOR_DIR": str(mask_operator.operator_out_dir),
            "PARAMETERS": str(parameters),
        }

        env_vars.update(envs)
        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/mitk-radiomics:{KAAPANA_BUILD_VERSION}",
            name="radiomics",
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            max_active_tis_per_dag=10,
            ram_mem_mb=3000,
            **kwargs
            )
