from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta
from typing import Union


class MinioOperator(KaapanaBaseOperator):
    """
    Operator to upload or download files to or from MinIO.

    """

    def __init__(
        self,
        dag,
        name="transfer-files-with-minio",
        action: str = "put",  # 'get', 'remove' or 'put'
        bucket_name: str = None,
        minio_prefix: str = "",
        batch_input_operators: list = [],
        none_batch_input_operators: list = [],
        action_files: list = [],
        whitelisted_file_extensions: Union[tuple, list] = (
            ".json",
            ".mat",
            ".py",
            ".zip",
            ".txt",
            ".gz",
            ".csv",
            ".pdf",
            ".png",
            ".jpg",
        ),
        zip_files: bool = False,
        **kwargs,
    ):
        """
        :param action: Action to execute. One of ('get', 'put'). Uppercase is ignored.
        :param bucket_name: Name of the Bucket to interact with, if empty or None defaults to the bucket of the project, in which dag-run was triggered.
        :param minio_prefix:
        :param batch_input_operators: List of operators, that store data in WORKFLOW_DIR/BATCH_NAME/<series-uid>/<operator.operator_out_dir>.
        :param none_batch_input_operators: List of operators, that store data in WORKFLOW_DIR/<operator.operator_out_dir>.
        :param action_files: Path to files where action should be applied on. If action=put, path is relative to WORKFLOW_DIR. If action=get path is relative to bucket_name/minio_prefix.
        :param whitelisted_file_extensions: Apply action only to files with specified file extensions.
        :param zip_files: If files should be zipped before the upload
        """
        assert action.lower() in ("get", "put")
        env_vars = {}

        envs = {
            "ACTION": action.lower(),
            "BUCKET_NAME": str(bucket_name),
            "MINIO_PREFIX": minio_prefix,
            "TARGET_FILES": ",".join(action_files),
            "WHITELISTED_FILE_EXTENSIONS": ",".join(whitelisted_file_extensions),
            "ZIP_FILES": str(zip_files),
            "BATCH_INPUT_OPERATORS": ",".join(
                [op.operator_out_dir for op in batch_input_operators]
            ),
            "NONE_BATCH_INPUT_OPERATORS": ",".join(
                [op.operator_out_dir for op in none_batch_input_operators]
            ),
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name=name,
            max_active_tis_per_dag=10,
            execution_timeout=timedelta(minutes=60),
            image=f"{DEFAULT_REGISTRY}/minio-operator:{KAAPANA_BUILD_VERSION}",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            ram_mem_mb=1000,
            **kwargs,
        )
