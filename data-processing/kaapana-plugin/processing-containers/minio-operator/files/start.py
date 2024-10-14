import datetime
import os
from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices, field_validator
from zipfile import ZipFile
from pathlib import Path
from typing import Any

from kaapanapy.helper import get_minio_client, load_workflow_config
from kaapanapy.settings import OperatorSettings
from minio import Minio


def get_project_bucket_name():
    """
    Return the name of the project bucket.
    """
    project = load_workflow_config().get("project_form")
    project_name = project.get("name")
    return f"project-{project_name}"


class MinioOperatorArguments(BaseSettings):
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

    input_directories: str = Field(
        "", validation_alias=AliasChoices("INPUT_DIRECTORIES")
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

    @field_validator("whitelisted_file_extensions", "target_files", "input_directories")
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
        settings.batch_name,
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


def upload_objects(
    input_directories,
    bucket_name,
    minio_prefix,
    zip_files,
    whitelisted_file_extensions,
    target_files,
):
    """
    - determine all directories, where files should be uploaded from
    - collect all files that should be uploaded
    - if zip_files is true, create a zip file of each source file
    - upload files to minio_prefix relative to bucket_name
    """
    settings = OperatorSettings()
    source_directories = []
    print("Start upload to MinIO!")
    print(f"Search for files in {input_directories=}")
    for directory in input_directories:
        source_directories.append(os.path.join(settings.workflow_dir, directory))

    print(f"{source_directories=}")
    minio_client: Minio = get_minio_client()

    print("Minio client ready!")
    zip_archive_file_path = Path("/tmp/zipped_files.zip")
    files_to_upload = []
    for source_directory in source_directories:
        print(f"glob {source_directory=}")
        files = [f for f in Path(source_directory).glob("**/*") if not f.is_dir()]
        print(f"{files=}")
        files_to_upload.extend(files)

        for file_path in files:
            if Path(file_path).suffix not in whitelisted_file_extensions:
                continue
            print(f"Collect {file_path=} for upload!")
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

    if target_files:
        print(f"{target_files=}")
        for file_path in target_files:
            if Path(file_path).suffix not in whitelisted_file_extensions:
                continue
            relative_file_path = Path(file_path).relative_to(
                Path(
                    settings.workflow_dir,
                )
            )
            if zip_files:
                with ZipFile(zip_archive_file_path, "w") as zip_file:
                    zip_file.write(file_name=file_path, arcname=relative_file_path)
            else:
                minio_file_path = os.path.join(minio_prefix, relative_file_path)
                minio_client.fput_object(
                    bucket_name=bucket_name,
                    file_path=file_path,
                    object_name=minio_file_path,
                )

    if zip_files:
        timestamp = (datetime.datetime.now()).strftime("%y-%m-%d-%H:%M:%S%f")
        run_id = OperatorSettings().run_id
        minio_path = f"{minio_prefix}/{run_id}_{timestamp}.zip"
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
    input_directories = operator_arguments.input_directories

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
