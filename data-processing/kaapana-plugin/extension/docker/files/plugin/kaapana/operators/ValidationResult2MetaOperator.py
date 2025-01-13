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


class ValidationResult2MetaOperator(KaapanaBaseOperator):
    """
    This operater pushes JSON data to OpenSearch.

    Pushes JSON data to the specified OpenSearch instance.
    If meta-data already exists, it can either be updated or replaced, depending on the no_update parameter.
    If the operator fails, some or no data is pushed to OpenSearch.
    Further information about OpenSearch can be found here: https://opensearch.org/docs/latest/

    **Inputs:**

    * JSON data that should be pushed to OpenSearch
    * DICOM data that is used to get the OpenSearch document ID

    **Outputs:**

    * If successful, the given JSON data is included in OpenSearch

    """

    def __init__(
        self,
        dag,
        name: str = "validation-result-to-meta",
        validator_output_dir: str = None,
        validation_tag: str = "00111001",
        opensearch_index=None,
        **kwargs,
    ):
        """
        Initializes the ValidationResult2MetaOperator.

        Args:
            dag (DAG): The DAG to which the operator belongs.
            validator_output_dir (str): Directory where validation output files are stored.
            validation_tag (str): Base tag used for validation (default: "00111001").
                    Multiple items of the validation results will be tagged by incrementing
                    this tag. e.g. 00111002, 00111003, ..
            name (str): Name of the operator
            opensearch_index (str): Index in OpenSearch where metadata will be stored (default: None).
            *args: Additional arguments for the parent class.
            **kwargs: Additional keyword arguments for the parent class.

        Returns:
            None
        """

        env_vars = {}

        if validator_output_dir is not None:
            env_vars["VALIDATOR_OUTPUT_DIR"] = validator_output_dir

        if opensearch_index is not None:
            env_vars["OPENSEARCH_INDEX"] = opensearch_index

        env_vars["VALIDATION_TAG"] = validation_tag

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/validation-result-to-meta:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs,
        )
