import os
from dataclasses import dataclass
from pathlib import Path

import requests
from kaapana_federated.utils import Encryption, TarUtils
from minio import Minio
from minio.deleteobjects import DeleteObject
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


@dataclass
class KaapanaInstance:
    instance_name: str
    fernet_key: str


@dataclass
class KaapanaJob:
    status: str  # finished, failed
    dag_id: str
    run_id: str
    id: int
    conf_data: dict

    @property
    def isFaild(self) -> bool:
        return self.status == "failed"

    @property
    def isFinished(self) -> bool:
        return self.status == "failed"


class KaapanaFedWorkflowService:
    """
    Connection of the Federated Orchestrator with the Backend
    """

    def __init__(self):
        service_namespace = os.getenv("SERVICES_NAMESPACE", None)
        assert service_namespace != None
        self.client_url = (
            f"http://kaapana-backend-service.{service_namespace}.svc:5000/client"
        )
        self.session = self._requests_retry_session()

    def _requests_retry_session(
        retries=16,
        backoff_factor=1,
        status_forcelist=[404, 429, 500, 502, 503, 504],
        session=None,
        use_proxies=False,
    ):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        if use_proxies is True:
            proxies = {
                "http": os.getenv("PROXY", None),
                "https": os.getenv("PROXY", None),
                "no_proxy": ".svc,.svc.cluster,.svc.cluster.local",
            }
            session.proxies.update(proxies)

        return session

    @staticmethod
    def _raise_for_status(r):
        if r.history:
            raise ConnectionError(
                "You were redirect to the auth page. Your token is not valid!"
            )
        try:
            r.raise_for_status()
        except:
            raise ValueError(
                f"Something was not okay with your request code {r}: {r.text}!"
            )

    def getThisInstance(self) -> KaapanaInstance:
        r = self.session.get(f"{self.client_url}/kaapana-instance")
        self._raise_for_status(r)
        return KaapanaInstance(**r.json())

    def getInstances(self, instance_names: list[str]) -> list[KaapanaInstance]:
        r = self.session.post.post(
            f"{self.client_url}/get-kaapana-instances",
            json={"instance_names": instance_names},
        )
        self._raise_for_status(r)
        return [KaapanaInstance(**obj) for obj in r.json()]

    def createJob(
        self,
        dag_id: str,
        conf_data: dict,
        username: str,
        instance_name: str,
        workflow_id: str,
    ) -> list[KaapanaJob]:
        payload = {
            "federated": True,
            "dag_id": dag_id,
            "instance_names": [instance_name],
            "workflow_id": workflow_id,
            "conf_data": conf_data,
            "username": username,
        }
        r = self.session.put(f"{self.client_url}/workflow_jobs", json=payload)
        self._raise_for_status(r)
        return [KaapanaJob(**obj) for obj in r.json()]

    def getJob(self, job_id: str) -> KaapanaJob:
        r = self.session.get(f"{self.client_url}/job", params={"job_id": job_id})
        self._raise_for_status(r)
        return KaapanaJob(**r.json())


class KaapanaFedDataService:
    """
    Connection of the Federated Orechestrator to retreive and send data to the remote sites
    """

    def __init__(
        self,
        bucket: str,
        federated_dir: str,
        operator_out_dir: str,
        access_key="kaapanaminio",
        secret_key="Kaapana2020",
        minio_host=None,
        minio_port="9000",
    ):
        if not minio_host:
            services_namespace = os.getenv("SERVICES_NAMESPACE", None)
            assert services_namespace != None
            minio_host = f"minio-service.{services_namespace}.svc"

        self.minioClient = Minio(
            minio_host + ":" + minio_port,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )
        self.bucket = bucket
        self.federated_dir = federated_dir
        self.operator_out_dir = operator_out_dir

    def _clean_up(self, path: str):
        delete_object_list = map(
            lambda x: DeleteObject(x.object_name),
            self.minioClient.list_objects(self.bucket, path, recursive=True),
        )
        errors = self.minioClient.remove_objects(self.bucket, delete_object_list)
        for error in errors:
            raise NameError("Error occured when deleting object", error)

    def clean_up(self):
        self._clean_up(self.federated_dir)

    def clean_up_round(self, federated_round: int, instance_name: str):
        path = self.federated_round_dir(federated_round)
        if path:
            self.log.info("Clean up data from previous round")
            self._clean_up(path / instance_name)

    def download(
        self, federated_round: int, instance_name: str, secret: str
    ) -> dict[Path, str]:
        path = self.federated_round_dir(federated_round) / instance_name
        self._download_package(path, secret)

    def _download_package(self, path: str, secret: str) -> dict[Path, str]:
        """Download files from Minio where remote workflows put them"""
        objects = self.minioClient.list_objects(self.bucket, path, recursive=True)

        # A mapping form the dowloaded file to the path on the minio backend
        file2serverObj = {}
        for obj in objects:
            if obj.is_dir:
                continue
            if not obj.object_name.endswith(".tar"):
                continue
            if (
                os.path.basename(obj.object_name).replace(".tar", "")
                not in self.remote_conf_data["federated_form"]["federated_operators"]
            ):
                # check if Tar file is actually from a federated operator
                continue
            if "from_server" in obj.object_name:
                continue

            relative_path = os.path.relpath(obj.object_name, self.federated_dir)
            file_path = Path(
                os.path.join(self.operator_out_dir, relative_path).replace(
                    "/from_client", ""
                )
            )
            file_path.parent.mkdir(exist_ok=True)
            self.minioClient.fget_object(self.bucket, obj.object_name, file_path)
            # Process Downloaded File
            Encryption.decryptfile(file_path, secret)
            TarUtils.untar(file_path, file_path.parent)
            file2serverObj[file_path] = obj.object_name
        return file2serverObj

    def upload_package(self, local_path, server_target_path, secret: str) -> None:
        file_path = file_path.replace("/from_client", "")
        file_path = file_path.replace("/from_server", "")
        file_dir = file_path.replace(".tar", "")
        TarUtils.tar(file_path, file_dir)
        Encryption.encryptfile(file_path, secret)

        server_target_path = server_target_path.replace("from_client", "from_server")
        self.log.info("Upload %s to %s", file_path, server_target_path)
        self.minioClient.fput_object(
            self.bucket,
            server_target_path,
            file_path,
        )

    def federated_round_dir(self, federated_round: int) -> Path:
        if federated_round < 0:
            return None
        return self.federated_dir / str(federated_round)
