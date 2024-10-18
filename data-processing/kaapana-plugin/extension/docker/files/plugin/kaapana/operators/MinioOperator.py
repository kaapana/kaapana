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

    **Upload**
    This operator supports three ways to specify data that should be uploaded:
    1. Specify a list of operators in batch_input_operators, where each operator stores its output in the following directories /WORKFLOW_DIR/BATCH_NAME/<series-uid>/operator.operator_out_dir.
    2. Specify a list of operators in none_batch_input_operators, where each operator stores its output in the following directories /WORKFLOW_DIR/operator.operator_out_dir.
    3. Specify a list of file paths relative to WORKFLOW_DIR in source_files
    The data will be uploaded to the minio bucket bucket_name relative to minio_prefix, i.e.
    the path of the destination file relative to minio_prefix is the same as the relative path of the source file to WORKFLOW_DIR.

    **Download**
    To download data from MinIO you must specify bucket_name, minio_prefix and source_files.
    Paths in source files must be relative to the minio_prefix in the bucket_name i.e. bucket_name/minio_prefix/<path-to-source-file>.
    Data is downloaded to WORKFLOW_DIR/operator_out_dir.
    The path of the destination file relative to WORKFLOW_DIR/operator_out_dir is the same as the relative path of the source file to minio_prefix.
    whitelisted_file_extension is ignored


    **Raises**
    * ValueError: If no file was processed.
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
        source_files: list = [],
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
            Can be overwritten by workflow_config.
        :param minio_prefix: A subpath of the minio_bucket, where files are uploaded or downloaded relative to. Can be overwritten by workflow_config.
        :param batch_input_operators: List of operators, that store data in WORKFLOW_DIR/BATCH_NAME/<series-uid>/<operator.operator_out_dir>.
        :param none_batch_input_operators: List of operators, that store data in WORKFLOW_DIR/<operator.operator_out_dir>.
        :param source_files: Path to files additional files, where action should be applied on.
            If action=put, path is relative to WORKFLOW_DIR.
            If action=get path is relative to bucket_name/minio_prefix.
            Can be overwritten by workflow_config["action_files"].
        :param whitelisted_file_extensions: List of file extensions that should exclusively considered when uploading to minio. Can be overwritten by workflow_config.
        :param zip_files: If files should be zipped before the upload. Can be overwritten by workflow_config.
        """
        assert action.lower() in ("get", "put")
        env_vars = {}

        envs = {
            "ACTION": action.lower(),
            "BUCKET_NAME": str(bucket_name),
            "MINIO_PREFIX": minio_prefix,
            "SOURCE_FILES": ",".join(source_files),
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
