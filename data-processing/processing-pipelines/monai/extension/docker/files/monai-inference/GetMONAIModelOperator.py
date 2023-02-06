from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version


class GetMONAIModelOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=None,
                 models=str("all"),
                 env_vars=None,
                 enable_proxy=True,
                 **kwargs
                 ):

        
        if env_vars is None:
            env_vars = {
                "MODELS": models,
            }

        super().__init__(
            dag=dag,
            name='get-monai-model',
            image=f"{default_registry}/monai-get-models:0.1.1",
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            enable_proxy=enable_proxy,
            env_vars=env_vars,
            **kwargs
        )