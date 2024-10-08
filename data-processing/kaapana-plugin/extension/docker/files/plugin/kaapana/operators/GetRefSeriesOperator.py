from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta
import json


class GetRefSeriesOperator(KaapanaBaseOperator):
    """Operator to get DICOM series in dependency of certain search filters.
    This can be used to:
    - download a reference series from a PACS system. (reference_uid).
    - download all series of a study from a PACS system. (study_uid)
    - NOT IMPLEMENTED YET: download all series of a patient from a PACS system. (patient_uid)

    This can be additinally filtered by OpenSearch metadata.
    """

    def __init__(
        self,
        dag,
        name: str = "get-ref-series",
        search_policy: str = "reference_uid",  # reference_uid, study_uid, patient_uid
        data_type: str = "dicom",  # dicom, json (NOT IMPLEMENTED YET)
        dicom_tags: list = [],  # list of dicom tags to filter the series
        parallel_downloads: int = 3,
        **kwargs,
    ):
        """Operator to get DICOM series in dependency of certain search filters.

        Args:
            dag (DAG): The DAG object.
            name (str, optional): The name of the operator. Defaults to "get-ref-series".
            search_policy (str, optional): The search policy to filter the series. Can be "reference_uid" or "study_uid". Defaults to "reference_uid".
            data_type (str, optional): The type of data to download. Defaults to "dicom".
            dicom_tags (list, optional): List of DICOM tags to filter the series. Defaults to [].
            parallel_downloads (int, optional): Number of parallel downloads. Defaults to 3.
        """

        env_vars = {}

        envs = {
            "DATA_TYPE": data_type,
            "SEARCH_POLICY": search_policy,
            "PARALLEL_DOWNLOADS": parallel_downloads,
            "DICOM_TAGS": json.dumps(dicom_tags),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/get-ref-series:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs,
        )
