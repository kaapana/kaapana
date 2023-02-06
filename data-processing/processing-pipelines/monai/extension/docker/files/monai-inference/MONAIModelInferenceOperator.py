from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version


class MONAIModelInferenceOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=None,
                 env_vars=None,
                 minio_data_input_bucket=None,
                 **kwargs
                 ):

        
        if env_vars is None:
            env_vars = {
                "MONAI_DATA_INPUT_BUCKET": minio_data_input_bucket,
            }

        super().__init__(
            dag=dag,
            name='monai-inference',
            image=f"{default_registry}/monai-inference:0.1.1",
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs
        )