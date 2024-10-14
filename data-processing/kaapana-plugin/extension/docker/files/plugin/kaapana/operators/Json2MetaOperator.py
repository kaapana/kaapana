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


class Json2MetaOperator(KaapanaBaseOperator):

    def __init__(
        self,
        dag,
        name="json2meta",
        dicom_operator=None,
        json_operator=None,
        jsonl_operator=None,
        set_dag_id: bool = False,
        no_update: bool = False,
        avalability_check_delay: int = 10,
        avalability_check_max_tries: int = 15,
        **kwargs,
    ):
        """
        :param dicom_operator: Used to get OpenSearch document ID from dicom data. Only used with json_operator.
        :param json_operator: Provides json data, use either this one OR jsonl_operator.
        :param jsonl_operator: Provides json data, which is read and pushed line by line. This operator is prioritized over json_operator.
        :param set_dag_id: Only used with json_operator. Setting this to True will use the dag run_id as the OpenSearch document ID when dicom_operator is not given.
        :param no_update: If there is a series found with the same ID, setting this to True will replace the series with new data instead of updating it.
        :param avalability_check_delay: When checking for series availability in PACS, this parameter determines how many seconds are waited between checks in case series is not found.
        :param avalability_check_max_tries: When checking for series availability in PACS, this parameter determines how often to check for series in case it is not found.
        """

        env_vars = {}

        if dicom_operator is not None:
            env_vars["DICOM_OPERATOR_OUT_DIR"] = dicom_operator.operator_out_dir

        if json_operator is not None:
            env_vars["JSON_OPERATOR_OUT_DIR"] = json_operator.operator_out_dir

        if jsonl_operator is not None:
            env_vars["JSONL_OPERATOR_OUT_DIR"] = jsonl_operator.operator_out_dir

        env_vars["AVALABILITY_CHECK_DELAY"] = str(avalability_check_delay)
        env_vars["AVALABILITY_CHECK_MAX_TRIES"] = str(avalability_check_max_tries)
        env_vars["SET_DAG_ID"] = str(set_dag_id)
        env_vars["NO_UPDATE"] = str(no_update)

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/json2meta:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs,
        )
