import os
import pathlib
from datetime import timedelta
import logging
import requests
import xml.etree.ElementTree as ET

from minio import Minio
from minio.error import InvalidResponseError, S3Error

from kaapana.blueprints.kaapana_global_variables import (
    SERVICES_NAMESPACE,
)

logger = logging.getLogger(__name__)


class HelperMinio(Minio):
    """
    Helper class for making authorized requests to the minio API
    """

    def __init__(
        self,
        dag_run=None,
        username: str = None,
        access_token: str = None,
    ):
        """
        :param dag_run: Airflow dag object.
        :param username: Username of the keycloak user that wants to communicate with minio.
        :access_token: Access token that should be used for communication with minio.
        """

        super().__init__(
            f"minio-service.{SERVICES_NAMESPACE}.svc:9000",
            access_key=os.environ.get("MINIOUSER"),
            secret_key=os.environ.get("MINIOPASSWORD"),
            secure=False,
        )

    def put_file(self, bucket_name, object_name, file_path):
        print(f"Creating bucket {bucket_name} if it does not already exist.")
        self.make_bucket(bucket_name)
        print(f"Putting file: {file_path} to {bucket_name} to {object_name}")
        try:
            super().fput_object(bucket_name, object_name, file_path)
        except InvalidResponseError as err:
            print(err)
            raise

    def get_file(self, bucket_name, object_name, file_path):
        print(f"Getting file: {object_name} from {bucket_name} to {file_path}")
        try:
            super().stat_object(bucket_name, object_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            super().fget_object(bucket_name, object_name, file_path)
        except S3Error as err:
            print(f"Skipping object {object_name} since it doe not exists in Minio")
        except InvalidResponseError as err:
            print(err)

    def remove_file(self, bucket_name, object_name):
        print(f"Removing file: {object_name} from {bucket_name}")
        try:
            super().remove_object(bucket_name, object_name)
        except InvalidResponseError as err:
            print(err)
            raise

    def apply_action_to_file(
        self, action, bucket_name, object_name, file_path, file_white_tuples=None
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
            self.get_file(bucket_name, object_name, file_path)
        elif action == "remove":
            self.remove_file(bucket_name, object_name)
        elif action == "put":
            self.put_file(bucket_name, object_name, file_path)
        else:
            raise NameError("You need to define an action: get, remove or put!")

    def apply_action_to_object_names(
        self,
        action,
        bucket_name,
        local_root_dir,
        object_names=None,
        file_white_tuples=None,
    ):
        for object_name in object_names:
            file_path = os.path.join(local_root_dir, object_name)
            if action != "put" or os.path.isfile(file_path):
                self.apply_action_to_file(
                    action,
                    bucket_name,
                    object_name,
                    file_path,
                    file_white_tuples,
                )

    def apply_action_to_object_dirs(
        self,
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
                        self.apply_action_to_file(
                            action,
                            bucket_name,
                            object_name,
                            file_path,
                            file_white_tuples,
                        )
        else:
            try:
                for bucket_obj in self.list_objects(bucket_name, recursive=True):
                    object_name = bucket_obj.object_name
                    file_path = os.path.join(local_root_dir, object_name)
                    path_object_name = pathlib.Path(object_name)
                    if not object_dirs or str(path_object_name.parents[0]).startswith(
                        tuple(object_dirs)
                    ):
                        self.apply_action_to_file(
                            action,
                            bucket_name,
                            object_name,
                            file_path,
                            file_white_tuples,
                        )
            except S3Error as err:
                print(f"Skipping since bucket {bucket_name} does not exist")

    def make_bucket(self, bucket_name):
        try:
            super().make_bucket(bucket_name=bucket_name, location="eu-central-1")
            print("created!")
        except S3Error as err:
            pass
        except InvalidResponseError as err:
            print(err)
            raise

    def get_presigned_link(self, bucket_name, object_name, expires=timedelta(days=2)):
        print("Generating link...")
        try:
            return super().presigned_get_object(
                bucket_name, object_name, expires=expires
            )
        except InvalidResponseError as err:
            print(err)
            raise

    def list_objects(self, *args, **kwargs):
        try:
            return super().list_objects(*args, **kwargs)
        except InvalidResponseError as err:
            print(err)
            raise
