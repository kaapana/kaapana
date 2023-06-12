import os
import pathlib
from datetime import timedelta

from minio import Minio
from minio.error import InvalidResponseError, S3Error
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class HelperMinio:
    _minio_host = f"minio-service.{SERVICES_NAMESPACE}.svc"
    _minio_port = "9000"
    minioClient = Minio(
        _minio_host + ":" + _minio_port,
        access_key=os.environ.get("MINIOUSER"),
        secret_key=os.environ.get("MINIOPASSWORD"),
        secure=False,
    )

    @staticmethod
    def apply_action_to_file(
        minioClient, action, bucket_name, object_name, file_path, file_white_tuples=None
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
            print(f"Getting file: {object_name} from {bucket_name} to {file_path}")
            try:
                minioClient.stat_object(bucket_name, object_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                minioClient.fget_object(bucket_name, object_name, file_path)
            except S3Error as err:
                print(f"Skipping object {object_name} since it doe not exists in Minio")
            except InvalidResponseError as err:
                print(err)
        elif action == "remove":
            print(f"Removing file: {object_name} from {bucket_name}")
            try:
                minioClient.remove_object(bucket_name, object_name)
            except InvalidResponseError as err:
                print(err)
                raise
        elif action == "put":
            print(f"Creating bucket {bucket_name} if it does not already exist.")
            HelperMinio.make_bucket(minioClient, bucket_name)
            print(f"Putting file: {file_path} to {bucket_name} to {object_name}")
            try:
                minioClient.fput_object(bucket_name, object_name, file_path)
            except InvalidResponseError as err:
                print(err)
                raise
        else:
            raise NameError("You need to define an action: get, remove or put!")

    @staticmethod
    def apply_action_to_object_names(
        minioClient,
        action,
        bucket_name,
        local_root_dir,
        object_names=None,
        file_white_tuples=None,
    ):
        for object_name in object_names:
            file_path = os.path.join(local_root_dir, object_name)
            if action != "put" or os.path.isfile(file_path):
                HelperMinio.apply_action_to_file(
                    minioClient,
                    action,
                    bucket_name,
                    object_name,
                    file_path,
                    file_white_tuples,
                )

    @staticmethod
    def apply_action_to_object_dirs(
        minioClient,
        action,
        bucket_name,
        local_root_dir,
        object_dirs=None,
        file_white_tuples=None,
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
                        HelperMinio.apply_action_to_file(
                            minioClient,
                            action,
                            bucket_name,
                            object_name,
                            file_path,
                            file_white_tuples,
                        )
        else:
            try:
                for bucket_obj in minioClient.list_objects(bucket_name, recursive=True):
                    object_name = bucket_obj.object_name
                    file_path = os.path.join(local_root_dir, object_name)
                    path_object_name = pathlib.Path(object_name)
                    if not object_dirs or str(path_object_name.parents[0]).startswith(
                        tuple(object_dirs)
                    ):
                        HelperMinio.apply_action_to_file(
                            minioClient,
                            action,
                            bucket_name,
                            object_name,
                            file_path,
                            file_white_tuples,
                        )
            except S3Error as err:
                print(f"Skipping since bucket {bucket_name} does not exist")

    @staticmethod
    def make_bucket(minioClient, bucket_name):
        try:
            minioClient.make_bucket(bucket_name=bucket_name, location="eu-central-1")
            print("created!")
        except S3Error as err:
            pass
        except InvalidResponseError as err:
            print(err)
            raise

    @staticmethod
    def get_presigned_link(
        minioClient, bucket_name, object_name, expires=timedelta(days=2)
    ):
        print("Generating link...")
        try:
            return minioClient.presigned_get_object(
                bucket_name, object_name, expires=expires
            )
        except InvalidResponseError as err:
            print(err)
            raise

    @staticmethod
    def list_objects(minioClient, *args, **kwargs):
        try:
            return minioClient.list_objects(*args, **kwargs)
        except InvalidResponseError as err:
            print(err)
            raise
