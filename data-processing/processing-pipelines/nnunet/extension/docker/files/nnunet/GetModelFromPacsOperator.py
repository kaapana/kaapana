from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class GetModelFromPacsOperator(KaapanaBaseOperator):
    """
    Downloads series that belong to an nnunet model from the PACS.

    The operator expects a list called 'tasks' in the workflow_config
    The list must contain values for the dicom tag '00181030 ProtocolName_keyword.keyword'
    The operator queries the project index in opensearch for all series that belong to these 'protocols'.
    The operator will download these series from the PACS.
    """

    def __init__(
        self,
        dag,
        name="get-model-from-pacs",
        **kwargs,
    ):
        """ """

        env_vars = {}

        envs = {}

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/nnunet-model-download-from-pacs:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb_lmt=10000,
            **kwargs,
        )
