import json
from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class GetRefSeriesOperator(KaapanaBaseOperator):
    """Operator to get DICOM series in dependency of certain search filters.
    This can be used to:
    - download a reference series (SEG or RTSTRUCT). (reference_uid).
    - download all series of a study. This can be additinally filtered by an OpenSearch query.(study_uid)
    - download series based on a OpenSearch search query. (search_query)
    """

    def __init__(
        self,
        dag,
        name: str = "get-ref-series",
        search_policy: str = "reference_uid",
        data_type: str = "dicom",
        search_query: dict = {},
        parallel_downloads: int = 3,
        modalities: list = [],
        custom_tags: list = [],
        skip_empty_ref_dir: bool = False,
        **kwargs,
    ):
        """Operator to get DICOM series in dependency of certain search filters.

        Args:
            dag (DAG): The DAG object.
            name (str, optional): The name of the operator. Defaults to "get-ref-series".
            search_policy (str, optional): The search policy to filter the series. Can be "reference_uid", "study_uid" or "search_query". Defaults to "reference_uid". "reference_uid" downloads the reference series of a SEG or RTSTRUCT, "study_uid" downloads all series of a study, "search_query" downloads all series based on a search query.
            data_type (str, optional): The type of data to download. Can be "dicom" or "json". Defaults to "dicom".
            search_query (list, optional): The search query for opensearch. Syntax must be the same as for opensearch. Defaults to {}. Must be a bool query (https://opensearch.org/docs/latest/query-dsl/compound/bool).
            parallel_downloads (int, optional): Number of parallel downloads. Defaults to 3.
            modalities (list, optional): List of modalities to filter the series. Defaults to []. Cant be used together with search_query. Only makes sense in conjunction with search_policy="study_uid".
            custom_tags (list, optional): List of custom tags to filter the series. Defaults to []. Cant be used together with search_query. Only makes sense in conjunction with search_policy="study_uid".
            skip_empty_ref_dir (bool): If true, it allows to skip empty reference directories, for series where no operator_in_dir exists
        """

        env_vars = {}

        envs = {
            "SEARCH_POLICY": search_policy,
            "DATA_TYPE": data_type,
            "SEARCH_QUERY": json.dumps(search_query),
            "PARALLEL_DOWNLOADS": str(parallel_downloads),
            "MODALITIES": json.dumps(modalities),
            "CUSTOM_TAGS": json.dumps(custom_tags),
            "SKIP_EMPTY_REF_DIR": str(skip_empty_ref_dir),
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
