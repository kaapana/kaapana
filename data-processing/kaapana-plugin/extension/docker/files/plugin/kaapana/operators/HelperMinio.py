import logging
import os
import pathlib


from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


def apply_action_to_file(
    minio_client: Minio,
    action,
    bucket_name,
    object_name,
    file_path,
    file_white_tuples=None,
):
    print(file_path)
    if file_white_tuples is not None and not file_path.lower().endswith(
        file_white_tuples
    ):
        print(
            f"Not applying action to object {object_name}, since this action is only allowed for files that end with {file_white_tuples}!"
        )
        return
    if action == "get":
        minio_client.get_object(bucket_name, object_name, file_path)
    elif action == "remove":
        minio_client.remove_object(bucket_name, object_name)
    elif action == "put":
        minio_client.fput_object(bucket_name, object_name, file_path)
    else:
        raise NameError("You need to define an action: get, remove or put!")


def apply_action_to_object_names(
    minio_client: Minio,
    action,
    bucket_name,
    local_root_dir,
    object_names=None,
    file_white_tuples=None,
    target_dir_prefix=None,
):
    for object_name in object_names:
        file_path = os.path.join(local_root_dir, object_name)

        # append directory prefix before object name
        # to store inside target directory of the bucket
        # only for `put` action
        if action == "put" and target_dir_prefix and target_dir_prefix != "":
            object_name = os.path.join(target_dir_prefix, object_name)

        if action != "put" or os.path.isfile(file_path):
            apply_action_to_file(
                minio_client=minio_client,
                action=action,
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                file_white_tuples=file_white_tuples,
            )


def apply_action_to_object_dirs(
    minio_client: Minio,
    action,
    bucket_name,
    local_root_dir,
    object_dirs=None,
    file_white_tuples=None,
    target_dir_prefix=None,
):
    object_dirs = object_dirs or []
    if action == "put":
        if not object_dirs:
            print(f"Uploading everything from {local_root_dir}")
            object_dirs = [""]
        for object_dir in object_dirs:
            for path, _, files in os.walk(os.path.join(local_root_dir, object_dir)):
                for name in files:
                    file_path = os.path.join(path, name)
                    rel_dir = os.path.relpath(path, local_root_dir)
                    rel_dir = "" if rel_dir == "." else rel_dir
                    object_name = os.path.join(rel_dir, name)

                    # append directory prefix before object name
                    # to store inside target directory of the bucket
                    if target_dir_prefix and target_dir_prefix != "":
                        object_name = os.path.join(target_dir_prefix, object_name)

                    apply_action_to_file(
                        minio_client=minio_client,
                        action=action,
                        bucket_name=bucket_name,
                        object_name=object_name,
                        file_path=file_path,
                        file_white_tuples=file_white_tuples,
                    )
    else:
        try:
            for bucket_obj in minio_client.list_objects(bucket_name, recursive=True):
                object_name = bucket_obj.object_name
                file_path = os.path.join(local_root_dir, object_name)
                path_object_name = pathlib.Path(object_name)
                if not object_dirs or str(path_object_name.parents[0]).startswith(
                    tuple(object_dirs)
                ):
                    apply_action_to_file(
                        minio_client=minio_client,
                        action=action,
                        bucket_name=bucket_name,
                        object_name=object_name,
                        file_path=file_path,
                        file_white_tuples=file_white_tuples,
                    )
        except S3Error as err:
            print(f"Skipping since bucket {bucket_name} does not exist")
