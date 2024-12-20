from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class DeleteFromPacsOperator(KaapanaBaseOperator):
    """This operator removes either selected series or whole studies from Kaapana's integrated PACS."""

    """
    An Airflow operator for removing selected series or entire studies from Kaapana's integrated PACS.

    This operator provides functionality to delete DICOM data from the PACS server, either at the series level or by deleting all series associated with a specified study.

    Execution Behavior:
        - Deletes selected series or the entire study from the PACS.
        - Limits to a maximum of 10 active tasks in the DAG (`max_active_tis_per_dag=10`).
        - Has an execution timeout of 60 minutes (`execution_timeout=timedelta(minutes=60)`).

    Attributes:
        name (str): The name of the operator (default: "delete-from-pacs").
        delete_complete_study (bool): Indicates whether to delete the entire study. Overrides individual series deletion if enabled (default: False).

    Args:
        dag (airflow.models.DAG): The DAG object to which the operator belongs.
        name (str, optional): The name assigned to the operator (default: "delete-from-pacs").
        delete_complete_study (bool, optional): If True, deletes all series associated with a study. The workflow's configuration overrides this argument (default: False).
        **kwargs: Additional arguments passed to the `KaapanaBaseOperator` constructor.

    Raises:
        N/A: This class does not raise specific errors beyond those handled by `KaapanaBaseOperator`.
    """

    def __init__(
        self,
        dag,
        name="delete-from-pacs",
        delete_complete_study=False,
        **kwargs,
    ):
        """
        :param delete_complete_study: Specifies the amount of removed data to all series of a specified study. The configuration of the workflow takes precedence over this argument.
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
