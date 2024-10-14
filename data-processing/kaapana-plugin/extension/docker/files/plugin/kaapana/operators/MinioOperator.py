from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)
from datetime import timedelta


class MinioOperator(KaapanaBaseOperator):
    """
    Operator to upload or download files to or from MinIO.

    """

    def __init__(
        self,
        dag,
        name="get-data-from-minio",
        action: str = "get",  # 'get', 'remove' or 'put'
        bucket_name: str = None,
        minio_prefix: str = "",
        action_operators: list = [],
        action_operator_dirs: list = [],
        action_files: list = [],
        file_white_tuples: tuple = (),
        zip_files: bool = False,
        **kwargs,
    ):
        """
        :param action: Action to execute ('get', 'remove' or 'put')
        :param bucket_name: Name of the Bucket to interact with, if empty or None defaults to the project bucket of the workflow.
        :param action_operators: Operator to use the output data from
        :param action_operator_dirs: (Additional) directory to apply MinIO
            action on.
        :param action_files: (Additional) files to apply MinIO action on.
        :param file_white_tuples: Optional whitelisting for files
        :param zip_files: If files should be zipped
        """

        env_vars = {}

        input_direcoties = [operator.operator_out_dir for operator in action_operators]
        input_direcoties.extend(action_operator_dirs)
        envs = {
            "ACTION": action,
            "BUCKET_NAME": str(bucket_name),
            "MINIO_PREFIX": minio_prefix,
            "TARGET_FILES": ",".join(action_files),
            "WHITELISTED_FILE_EXTENSIONS": ",".join(file_white_tuples),
            "ZIP_FILES": str(zip_files),
            "INPUT_DIRECTORIES": ",".join(input_direcoties),
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
