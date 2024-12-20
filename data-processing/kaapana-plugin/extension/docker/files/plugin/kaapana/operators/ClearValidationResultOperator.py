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
    Clears validation results from OpenSearch and Minio.
    """

    def __init__(
        self,
        dag,
        name="clear-validation-results",
        static_results_dir: str = "staticwebsiteresults",
        validation_tag: str = "00111001",
        opensearch_index=None,
        **kwargs,
    ):
        """
        :param dag (DAG): The DAG to which the operator belongs.
        :param name (str, optional): The name of the operator. Defaults to "clear-validation-results".
        :param static_results_dir (str, optional): directory inside the bucket which stores the validation results html files. Defaults to "staticwebsiteresults".
            associated bucket name from the project will be taken from the project form.
        :param validation_tag (str, optional): Base tag used to store validation results on OpenSearch (default: "00111001").
        :param opensearch_index (_type_, optional): Index in OpenSearch where metadata will be stored. Defaults to OpensearchSettings().default_index.
        """

        env_vars = {}

        env_vars["STATIC_RESULTS_DIR"] = static_results_dir
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
