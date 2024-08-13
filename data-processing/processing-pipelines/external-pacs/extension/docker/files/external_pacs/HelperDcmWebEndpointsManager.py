import logging
from typing import List

from kaapana.operators.HelperMinio import HelperMinio

logger = logging.getLogger(__name__)


class HelperDcmWebEndpointsManager:
    def __init__(
        self,
        bucket_name: str = "external-pacs",
        object_name: str = "external-pacs.json",
        dag_run=None,
    ):
        if dag_run:
            self.minio_client = HelperMinio(dag_run=dag_run)
        else:
            self.minio_client = HelperMinio(username="system")

        self.bucket_name = bucket_name
        self.object_name = object_name

    def add_endpoint(self, dcmweb_endpoint: str):
        endpoints = self.minio_client.get_json(self.bucket_name, self.object_name)
        endpoints.append(dcmweb_endpoint)
        self.minio_client.put_json(self.bucket_name, self.object_name, data=endpoints)
        if dcmweb_endpoint not in self.minio_client.get_json(
            self.bucket_name, self.object_name
        ):
            logger.error(
                f"{dcmweb_endpoint} could not be added to minio list of dcmweb_endpoints"
            )
            exit(1)

    def remove_endpoint(self, dcmweb_endpoint: str):
        endpoints = self.minio_client.get_json(self.bucket_name, self.object_name)
        try:
            endpoints.remove(dcmweb_endpoint)
        except ValueError:
            logger.error(f"There is no {dcmweb_endpoint} to remove.")

        if not self.minio_client.put_json(
            self.bucket_name, self.object_name, data=endpoints
        ):
            logger.error("Couldn't update endpoint list")
            exit(1)
        if len(endpoints) == 0:
            self.minio_client.remove_file(self.bucket_name, self.object_name)

    def get_endpoints(self) -> List[str]:
        return self.minio_client.get_json(self.bucket_name, self.object_name)
