from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version


class DcmExtractorOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(seconds=30),
                 json_operator=None,
                 env_vars=None,
                 **kwargs
                 ):

        """
        :param json_operator: Provides input json data that is copied and extended with the slice_number and curated_modality key
        :param env_vars: Environment variables
        """
        
        if env_vars is None:
            env_vars = {}

        envs = {"OPERATOR_IN_JSON": json_operator.operator_out_dir}
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name='dcm-extractor',
            image=f"{default_registry}/dcm-extractor:{kaapana_build_version}",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            **kwargs
        )