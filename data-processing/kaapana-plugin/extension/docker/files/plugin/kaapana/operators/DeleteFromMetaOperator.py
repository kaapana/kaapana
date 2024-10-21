from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class DeleteFromMetaOperator(KaapanaBaseOperator):
    """
    Operator to remove series from OpenSearch's index.

    This operator removes either selected series or whole studies from OpenSearch's index for the functional unit Meta.
    The operator relies on OpenSearch's "delete_by_query" function.

    **Inputs:**

    * Input data which should be removed is given via input parameter: delete_operator.
    """

    def __init__(
        self,
        dag,
        name="delete-from-meta",
        delete_all_documents=False,
        delete_complete_study=False,
        **kwargs,
    ):
        """
        :param delete_all_documents: Specifies the amount of removed data to all documents.
        :param delete_complete_study: Specifies the amount of removed data to all series of a specified study.
        """

        env_vars = {}

        env_vars["DELETE_COMPLETE_STUDY"] = str(delete_complete_study)
        env_vars["DELETE_ALL_DOCUMENTS"] = str(delete_all_documents)

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/delete-from-meta:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs,
        )
