from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class GetModelFromPacsOperator(KaapanaBaseOperator):
    """
    Operator to get input data for a workflow/dag.

    This operator pulls all defined files from it's defined source and stores the files in the workflow directory.
    All subsequent operators can get and process the files from within the workflow directory.
    Typically, this operator can be used as the first operator in a workflow.


    **Outputs:**

    * Stores downloaded 'dicoms' or 'json' files in the 'operator_out_dir'
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
            ram_mem_mb=1000,
            **kwargs,
        )
