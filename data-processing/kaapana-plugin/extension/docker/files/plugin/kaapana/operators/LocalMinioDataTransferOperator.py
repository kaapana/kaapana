import math
import subprocess
import threading
import traceback
from datetime import timedelta
from queue import Queue
from typing import List, Set, Tuple

import requests
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper import get_minio_client
from kaapanapy.logger import get_logger
from minio import Minio
from minio.commonconfig import ComposeSource, CopySource
from minio.error import S3Error

logger = get_logger(__name__)


class LocalMinioDataTransferOperator(KaapanaPythonBaseOperator):
    """
    Operator to copy data between MinIO buckets with enhanced error handling and threading.

    This operator provides capabilities to:
    - Copy objects, including large files using multipart copy
    - Transfer files across multiple destination buckets in parallel
    """

    def get_project_by_name(self, project_name: str) -> dict:
        """
        Retrieve project details by project name from the AII service.

        :param project_name: Name of the project to retrieve
        :return: Project details dictionary
        :raises: requests.HTTPError if the request fails
        """
        response = requests.get(
            f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}",
            params={"name": project_name},
        )
        response.raise_for_status()
        return response.json()

    def list_objects(
        self, client, bucket_name, paths: List[str]
    ) -> Set[Tuple[str, int]]:
        """
        List all objects in a bucket with given prefix paths.

        :param client: Minio client
        :param bucket_name: Name of the source bucket
        :param paths: List of path prefixes to filter objects
        :return: Set of tuples containing (object_name, object_size)
        """
        all_objects = set()
        for obj in client.list_objects(bucket_name, recursive=True):
            if any(obj.object_name.startswith(path) for path in paths):
                all_objects.add((obj.object_name, obj.size))
        return all_objects

    def copy_large_object(self, client, source_bucket, dest_bucket, obj_name, size):
        """
        Copy large object using compose_object with proper range-based part copying.

        :param client: Minio client
        :param source_bucket: Source bucket name
        :param dest_bucket: Destination bucket name
        :param obj_name: Object name to copy
        :param size: Total size of the object in bytes
        :raises: S3Error if any part of the copy operation fails
        """
        try:
            part_size = 5 * 1024 * 1024 * 1024  # 5GB (S3 limit)
            num_parts = math.ceil(size / part_size)
            sources = []

            for i in range(num_parts):
                start = i * part_size
                end = min((i + 1) * part_size, size)
                part_name = f"{obj_name}.part{i}"

                # Create a copy source with specific byte range
                copy_source = CopySource(
                    bucket_name=source_bucket,
                    object_name=obj_name,
                    offset=start,
                    length=end - start,
                )

                # Copy the part to destination bucket
                client.copy_object(
                    bucket_name=dest_bucket, object_name=part_name, source=copy_source
                )

                # Prepare compose source for final composition
                sources.append(
                    ComposeSource(bucket_name=dest_bucket, object_name=part_name)
                )

            # Compose the final object from parts
            client.compose_object(
                bucket_name=dest_bucket, object_name=obj_name, sources=sources
            )

            # Clean up intermediate parts
            for source in sources:
                client.remove_object(
                    bucket_name=dest_bucket, object_name=source.object_name
                )

            logger.info(f"Large file copied: {obj_name}")

        except S3Error as e:
            logger.error(f"Error copying large file {obj_name}: {e}")
            raise

    def copy_object(
        self, client, source_bucket, dest_bucket, obj_name, size, error_queue=None
    ):
        """
        Copy an object, using multipart upload if necessary.

        :param client: Minio client
        :param source_bucket: Source bucket name
        :param dest_bucket: Destination bucket name
        :param obj_name: Object name to copy
        :param size: Total size of the object in bytes
        :param error_queue: Queue to collect any errors during copying
        :raises: S3Error if copying fails
        """
        try:
            if size > 5 * 1024 * 1024 * 1024:  # If > 5GB, use multipart copy
                self.copy_large_object(
                    client, source_bucket, dest_bucket, obj_name, size
                )
            else:
                # Simple copy for objects smaller than 5GB
                source = CopySource(bucket_name=source_bucket, object_name=obj_name)
                client.copy_object(
                    bucket_name=dest_bucket,
                    object_name=obj_name,
                    source=source,
                )
                logger.info(f"Copied: {obj_name}")

        except Exception as e:
            error_info = {
                "object_name": obj_name,
                "source_bucket": source_bucket,
                "dest_bucket": dest_bucket,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            if error_queue:
                error_queue.put(error_info)
            raise

    def process_files(self, client, source_bucket, dest_buckets, files_and_folders):
        """
        Processes file copy operations for multiple destination buckets.

        :param client: Minio client
        :param source_bucket: Source bucket name
        :param dest_buckets: List of destination bucket names
        :param files_and_folders: List of files and folders to copy
        :raises: Exception if any thread encounters an error during copying
        """
        all_objects = self.list_objects(client, source_bucket, files_and_folders)
        error_queue = Queue()
        threads = []

        for obj_name, size in all_objects:
            for dest_bucket in dest_buckets:
                thread = threading.Thread(
                    target=self.copy_object,
                    args=(
                        client,
                        source_bucket,
                        dest_bucket,
                        obj_name,
                        size,
                        error_queue,
                    ),
                )
                thread.start()
                threads.append(thread)

        for thread in threads:
            thread.join()

        if not error_queue.empty():
            errors = []
            while not error_queue.empty():
                errors.append(error_queue.get())

            # Raise an exception with all error details
            error_message = "Errors occurred during file copying:\n" + "\n".join(
                f"Object: {err['object_name']}, Source: {err['source_bucket']}, "
                f"Dest: {err['dest_bucket']}\nError: {err['error']}"
                for err in errors
            )
            raise Exception(error_message)

    def start(self, ds, **kwargs):
        """
        Main method to initiate the data transfer process.

        :param ds: Airflow's ds parameter (date)
        :param kwargs: Additional keyword arguments from Airflow context
        """
        dag_run = kwargs["dag_run"]
        conf = kwargs["dag_run"].conf
        print("conf", conf)
        source_bucket = conf["project_form"]["s3_bucket"]
        destination_projects = conf["workflow_form"]["projects"]
        destination_buckets = []
        for destination_project in destination_projects:
            destination_buckets.append(
                self.get_project_by_name(destination_project)["s3_bucket"]
            )
        logger.info(f"{source_bucket=}")
        logger.info(f"{destination_buckets=}")
        # Check if source_bucket is in destination_buckets
        if source_bucket in destination_buckets:
            logger.info(
                f"Source bucket {source_bucket} found in destination buckets. Removing it."
            )
            destination_buckets.remove(source_bucket)
            logger.info(f"{destination_buckets=}")
        # Check if destination_buckets is now empty
        if not destination_buckets:
            logger.info(
                "No destination buckets remain after removing source bucket. Nothing to do here."
            )
            return
        files_and_folders = conf["backend_form"]["selectedFilesAndFolders"]
        minio_client = get_minio_client()

        self.process_files(
            minio_client, source_bucket, destination_buckets, files_and_folders
        )

    def __init__(
        self,
        dag,
        name="minio-data-transfer",
        **kwargs,
    ):
        """
        Initialize the LocalMinioDataTransferOperator.

        :param dag: Airflow DAG object
        :param name: Name of the operator (default: minio-data-transfer)
        :param kwargs: Additional keyword arguments
        """
        super(LocalMinioDataTransferOperator, self).__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            execution_timeout=timedelta(minutes=360),
            **kwargs,
        )
