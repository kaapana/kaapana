import datetime
import os
from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices, field_validator
from zipfile import ZipFile
from pathlib import Path
from typing import Any

from kaapanapy.helper import get_minio_client, load_workflow_config
from kaapanapy.settings import OperatorSettings
from kaapanapy.logger import get_logger
from minio import Minio

logger = get_logger(__name__)


def get_project_bucket_name():
    """
    Return the name of the project bucket.
    The project is received form the workflow config.
    """
    project = load_workflow_config().get("project_form")
    project_name = project.get("name")
    return f"project-{project_name}"


class MinioOperatorArguments(BaseSettings):
    """
    This class parses the arguments given to the MinioOperator from environment variables.

    Comma separeted strings are parsed to list of strings.
    If the bucket_name is "None" or "" the project bucket is determined.
    The string zip_files is converted to a boolean.
    """

    action: str
    bucket_name: str = Field("", validation_alias="BUCKET_NAME")
    minio_prefix: str = Field("", validation_alias="MINIO_PREFIX")
    zip_files: bool = Field(True)
    whitelisted_file_extensions: str = Field("")
    target_files: str = Field(
        "",
        description="Explicit path to files on that action should be applied. The path is relative to minio_prefix and bucket_name",
        validation_alias=AliasChoices("ACTION_FILES", "TARGET_FILES"),
    )

    batch_input_operators: str = Field(
        "", validation_alias=AliasChoices("BATCH_INPUT_OPERATORS")
    )
    none_batch_input_operators: str = Field(
        "", validation_alias=AliasChoices("NONE_BATCH_INPUT_OPERATORS")
    )

    @field_validator("bucket_name", mode="before")
    @classmethod
    def set_bucket_to_project_bucket_if_empty(cls, v: Any):
        if v is None:
            return get_project_bucket_name()
        elif type(v) is str and (v.lower() == "none" or v == ""):
            return get_project_bucket_name()
        else:
            return v

    @field_validator(
        "whitelisted_file_extensions",
        "target_files",
        "batch_input_operators",
        "none_batch_input_operators",
    )
    @classmethod
    def list_from_commaseparated_string(cls, v: Any):
        if type(v) == str and v == "":
            return []
        elif type(v) == str:
            return v.split(",")
        else:
            raise TypeError(f"{v=} must be of type str but is {type(v)}")

    @field_validator("zip_files", mode="before")
    @classmethod
    def str_to_bool(cls, v: Any):
        if v == "True":
            return True
        elif v == "False":
            return False
        else:
            raise ValueError(f"zip_files must be one of ['True','False'] not v")


def download_objects(
    bucket_name, minio_prefix, whitelisted_file_extensions, target_files=None
):
    """
    - determine target directory
    - List all objects in bucket relative to subpath
    - Download files from minio_path for target directory
    """
    settings = OperatorSettings()
    target_dir = os.path.join(
        settings.workflow_dir,
        settings.operator_out_dir,
    )
    os.makedirs(target_dir, exist_ok=True)

    minio_client: Minio = get_minio_client()

    objects_available_in_minio = minio_client.list_objects(
        bucket_name=bucket_name, prefix=minio_prefix, recursive=True
    )

    objects_to_download = []
    if target_files:
        available_object_paths = [
            object.object_name for object in objects_available_in_minio
        ]
        for file_path in target_files:
            assert (
                file_path in available_object_paths
            ), f"{file_path=} from {target_files=} not found in {objects_available_in_minio=}"

    for object in objects_to_download:
        if object.is_dir:
            continue
        if Path(object.object_name).suffix not in whitelisted_file_extensions:
            continue
        target_path = os.path.join(target_dir, object.object_name)
        minio_client.fget_object(
            object.bucket_name, object_name=object.object_name, file_path=target_path
        )


def get_absolute_batch_operator_input_directories(
    batch_operator_input_directories: list,
):
    """
    Return a list of all absolute paths that match WORKFLOW_DIR/BATCH_NAME/<series-uid>/operator_out_dir
    for each operator_out_dir in <batch_operator_input_directories>.

    :param batch_operator_input_directories: List of directories that are operator_out_dir of an upstream operator.
    """
    workflow_batch_directory = Path(
        os.path.join(OperatorSettings().workflow_dir, OperatorSettings().batch_name)
    )
    if not workflow_batch_directory.is_dir():
        logger.warning(f"{workflow_batch_directory=} does not exist!")
    absolute_batch_operator_input_directories = []
    for series_directory in workflow_batch_directory.iterdir():
        for operator_in_dir in batch_operator_input_directories:
            batch_operator_directory = series_directory.joinpath(operator_in_dir)
            if not batch_operator_directory.is_dir():
                logger.warning(f"{batch_operator_directory=} does not exist!")
            absolute_batch_operator_input_directories.append(batch_operator_directory)
    return absolute_batch_operator_input_directories


def get_absolute_none_batch_operator_input_directories(
    none_batch_operator_input_directories: list,
):
    """
    Return a list of all absolute paths that match WORKFLOW_DIR/operator_out_dir
    for each operator_out_dir in <none_batch_operator_input_directories>.

    :param none_batch_operator_input_directories: List of directories that are operator_out_dir of an upstream operator.
    """
    workflow_directory = Path(OperatorSettings().workflow_dir)
    if not workflow_directory.is_dir():
        logger.warning(f"{workflow_directory=} does not exist!")

    absolute_operator_input_directories = []
    for operator_directory in none_batch_operator_input_directories:
        operator_in_dir = workflow_directory.joinpath(operator_directory)
        if not operator_in_dir.is_dir():
            logger.warning(f"{operator_in_dir=} does not exist!")
        absolute_operator_input_directories.append(operator_in_dir)
    return absolute_operator_input_directories


def upload_objects(
    bucket_name: str,
    minio_prefix: str,
    whitelisted_file_extensions: list,
    zip_files: bool = True,
    target_files: list = [],
    input_directories: list = [],
):
    """
    Upload files to Minio.

    :param input_directories: List of directories, from which files should be uploaded.
    :param bucket_name: The minio bucket, where the data will be uploaded.
    :param minio_prefix: A minio prefix relative to the bucket name, under which the data will be uploaded.
    :param zip_files: Whether the files should be zipped in a single archive before uploading them. Archive paths will be the paths relative to WORKFLOW_DIR.
    :param whitelisted_file_extensions: Exclusive list of file extensions, of files that will be uploaded.
    :param target_files: List of file paths relative to WORKFLOW_DIR, that should be uploaded

    - Collect all files that should be uploaded and match any extenstion in white_listed_file_extensions
    - If zip_files is true, create a archive of all collected files.
    - Upload either this archive or all collected files to minio_prefix relative to bucket_name

    Raises:
        * ValueError if no files were found to upload
    """
    settings = OperatorSettings()
    logger.info("Start upload to MinIO!")
    logger.info(f"Search for files in {input_directories=}")
    minio_client: Minio = get_minio_client()

    zip_archive_file_path = Path("/tmp/zipped_files.zip")
    files_to_upload = []

    for source_directory in input_directories:
        files = [f for f in Path(source_directory).glob("**/*") if not f.is_dir()]
        for file_path in files:
            if Path(file_path).suffix not in whitelisted_file_extensions:
                continue
            files_to_upload.append(file_path)
            logger.info(f"Collect {file_path=} for upload!")

    for file_path in target_files:
        if Path(file_path).suffix not in whitelisted_file_extensions:
            continue
        logger.info(f"Collect {file_path=} for upload!")

    if len(files_to_upload) == 0:
        logger.error("No files were collected for upload.")
        logger.error("Upstream tasks may file.")
        raise ValueError(f"No files were found for upload")

    for file_path in files_to_upload:
        relative_file_path = Path(file_path).relative_to(
            Path(
                settings.workflow_dir,
            )
        )
        if zip_files:
            with ZipFile(zip_archive_file_path, "w") as zip_file:
                zip_file.write(filename=file_path, arcname=relative_file_path)
        else:
            minio_file_path = os.path.join(minio_prefix, relative_file_path)
            minio_client.fput_object(
                bucket_name=bucket_name,
                file_path=file_path,
                object_name=minio_file_path,
            )

    if zip_files and len(files_to_upload) > 0:
        logger.info("Compress files into zip archive before uploading")
        timestamp = (datetime.datetime.now()).strftime("%y-%m-%d-%H:%M:%S%f")
        run_id = OperatorSettings().run_id
        minio_path = f"{bucket_name}/{minio_prefix}/{run_id}_{timestamp}.zip"
        logger.info(f"Upload archive to {minio_path=}.")
        minio_client.fput_object(
            bucket_name=bucket_name,
            file_path=zip_archive_file_path,
            object_name=minio_path,
        )


if __name__ == "__main__":
    operator_arguments = MinioOperatorArguments()
    workflow_config = load_workflow_config()

    # Arguments provides via workflow config are prioritized
    action = operator_arguments.action
    zip_files = workflow_config.get("zip_files") or operator_arguments.zip_files
    bucket_name = workflow_config.get("bucket_name") or operator_arguments.bucket_name
    minio_prefix = (
        workflow_config.get("minio_prefix") or operator_arguments.minio_prefix
    )
    whitelisted_file_extensions = (
        workflow_config.get("whitelisted_file_extensions")
        or operator_arguments.whitelisted_file_extensions
    )
    target_files = (
        workflow_config.get("target_files") or operator_arguments.target_files
    )
    batch_input_operator_directories = operator_arguments.batch_input_operators
    none_batch_input_operator_directories = (
        operator_arguments.none_batch_input_operators
    )

    input_directories = get_absolute_batch_operator_input_directories(
        batch_operator_input_directories=batch_input_operator_directories
    ) + get_absolute_none_batch_operator_input_directories(
        none_batch_operator_input_directories=none_batch_input_operator_directories
    )

    if action == "put":
        upload_objects(
            input_directories=input_directories,
            bucket_name=bucket_name,
            minio_prefix=minio_prefix,
            zip_files=zip_files,
            whitelisted_file_extensions=whitelisted_file_extensions,
            target_files=target_files,
        )
    elif action == "get":
        download_objects(
            bucket_name=bucket_name,
            minio_prefix=minio_prefix,
            whitelisted_file_extensions=whitelisted_file_extensions,
            target_files=target_files,
        )
