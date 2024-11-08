from datetime import timedelta

from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class GetInputOperator(KaapanaBaseOperator):
    """
    Operator to get input data for a workflow/dag.

    This operator pulls all defined files from it's defined source and stores the files in the workflow directory.
    All subsequent operators can get and process the files from within the workflow directory.
    Typically, this operator can be used as the first operator in a workflow.

    **Inputs:**

    * data_form: 'json'
    * data_type: 'dicom' or 'json'
    * dataset_limit: limit the download series list number
    * include_custom_tag_property: Key in workflow_form used to specify tags that must be present in the data for inclusion
    * exclude_custom_tag_property: Key in workflow_form used to specify tags that, if present in the data, lead to exclusion

    **Outputs:**

    * Stores downloaded 'dicoms' or 'json' files in the 'operator_out_dir'
    """

    def __init__(
        self,
        dag,
        name="get-input-data",
        data_type="dicom",
        # data_form=None,
        check_modality=False,
        # dataset_limit=None,
        parallel_downloads=3,
        include_custom_tag_property="",
        exclude_custom_tag_property="",
        batch_name=None,
        **kwargs,
    ):
        """
        :param data_type: 'dicom' or 'json'
        :param data_form: 'json'
        :param check_modality: 'True' or 'False'
        :param dataset_limit: limits the download list
        :param include_custom_tag_property: key in workflow_form for filtering with tags that must exist
        :param exclude_custom_tag_property: key in workflow_form for filtering with tags that must not exist
        :param parallel_downloads: default 3, number of parallel downloads
        """

        env_vars = {}

        envs = {
            "DATA_TYPE": data_type,
            "INCLUDE_CUSTOM_TAG_PROPERTY": include_custom_tag_property,
            "EXCLUDE_CUSTOM_TAG_PROPERTY": exclude_custom_tag_property,
            "BATCH_NAME": batch_name,
            "CHECK_MODALITY": "False" if not check_modality else "True",
            "PARALLEL_DOWNLOADS": str(parallel_downloads),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/get-input:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb_lmt=10000,
            batch_name=batch_name,
            **kwargs,
        )
