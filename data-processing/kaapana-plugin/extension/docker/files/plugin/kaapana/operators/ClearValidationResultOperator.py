from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings

logger = get_logger(__name__)

SERVICES_NAMESPACE = KaapanaSettings().services_namespace


class ClearValidationResultOperator(KaapanaBaseOperator):
    """
    Initializes the LocalClearValidationResultOperator.

    Args:
        dag (DAG): The DAG to which the operator belongs.
        name (str): The name of the operator. Defaults to "clear-validation-results".
        results_bucket (str): minio bucket which stores the validation results html files. Defaults to "staticwebsiteresults".
        validation_tag (str): Base tag used to store validation results on OpenSearch (default: "00111001").
        opensearch_index (str): Index in OpenSearch where metadata will be stored. Defaults to OpensearchSettings().default_index.
        *args: Additional arguments for the parent class.
        **kwargs: Additional keyword arguments for the parent class.

    Returns:
        None
    """

    def __init__(
        self,
        dag,
        name="clear-validation-results",
        result_bucket: str = "staticwebsiteresults",
        validation_tag: str = "00111001",
        opensearch_index=None,
        **kwargs,
    ):
        """Clears validation results from OpenSearch and Minio.

        Args:
            dag (DAG): The DAG to which the operator belongs.
            name (str, optional): The name of the operator. Defaults to "clear-validation-results".
            result_bucket (str, optional): minio bucket which stores the validation results html files. Defaults to "staticwebsiteresults".
            validation_tag (str, optional): Base tag used to store validation results on OpenSearch (default: "00111001").
            opensearch_index (_type_, optional): Index in OpenSearch where metadata will be stored. Defaults to OpensearchSettings().default_index.
        """

        env_vars = {}

        env_vars["RESULT_BUCKET"] = result_bucket
        env_vars["VALIDATION_TAG"] = validation_tag

        if opensearch_index is not None:
            env_vars["OPENSEARCH_INDEX"] = opensearch_index

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/clear-validation-results:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs,
        )
