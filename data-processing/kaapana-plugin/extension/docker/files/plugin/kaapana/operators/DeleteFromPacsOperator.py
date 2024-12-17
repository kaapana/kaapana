from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class DeleteFromPacsOperator(KaapanaBaseOperator):

    def __init__(
        self,
        dag,
        name="delete-from-pacs",
        delete_complete_study=False,
        **kwargs,
    ):
        """
        :param delete_complete_study: Specifies the amount of removed data to all series of a specified study.
        """

        env_vars = {}

        env_vars["DELETE_COMPLETE_STUDY"] = str(delete_complete_study)

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/delete-from-pacs:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs,
        )
