import json
import os
import requests
import logging
import functools
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests_cache import CachedSession
from datetime import timezone, timedelta
import datetime
from fastapi import HTTPException
from app.config import settings

from opensearchpy import OpenSearch
from minio import Minio
from urllib3.util import Timeout
import xml.etree.ElementTree as ET

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


TIMEOUT_SEC = 5
TIMEOUT = Timeout(TIMEOUT_SEC)


class HelperMinio(Minio):
    """
    Helper class for making authorized requests to the minio API
    """

    def __init__(
        self,
        access_token: str = None,
    ):
        """
        :access_token: Access token that should be used for communication with minio.
        """
        if access_token:
            self.access_token = access_token
            access_key, secret_key, session_token = self.minio_credentials()
        else:
            access_key, secret_key, session_token = (
                settings.minio_username,
                settings.minio_password,
                None,
            )

        super().__init__(
            f"minio-service.{settings.services_namespace}.svc:9000",
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            secure=False,
        )

    def minio_credentials(self):
        r = requests.post(
            f"http://minio-service.{settings.services_namespace}.svc:9000?Action=AssumeRoleWithWebIdentity&WebIdentityToken={self.access_token}&Version=2011-06-15"
        )
        xml_response = r.text
        root = ET.fromstring(xml_response)
        credentials = root.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}Credentials"
        )
        access_key_id = credentials.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}AccessKeyId"
        ).text
        secret_access_key = credentials.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}SecretAccessKey"
        ).text
        session_token = credentials.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}SessionToken"
        ).text
        return access_key_id, secret_access_key, session_token

    def get_custom_presigend_url(
        self, method, bucket_name, object_name, expires=timedelta(days=7)
    ):
        if method not in ["GET", "PUT"]:
            raise NameError("Method must be either GET or PUT")
        presigend_url = self.get_presigned_url(
            method, bucket_name, object_name, expires=expires
        )
        return {
            "method": method.lower(),
            "path": presigend_url.replace(
                f"{self._base_url._url.scheme}://{self._base_url._url.netloc}",
                "",
            ),
        }

    def add_minio_urls(self, federated, instance_name):
        federated_dir = federated["federated_dir"]
        federated_bucket = federated["federated_bucket"]
        if "federated_round" in federated:
            federated_round = str(federated["federated_round"])
        else:
            federated_round = ""

        if not self.bucket_exists(federated_bucket):
            self.make_bucket(federated_bucket)

        minio_urls = {}
        for federated_operator in federated["federated_operators"]:
            minio_urls[federated_operator] = {
                "get": self.get_custom_presigend_url(
                    "GET",
                    federated_bucket,
                    os.path.join(
                        federated_dir,
                        federated_round,
                        instance_name,
                        f"{federated_operator}.tar",
                    ),
                ),
                "put": self.get_custom_presigend_url(
                    "PUT",
                    federated_bucket,
                    os.path.join(
                        federated_dir,
                        federated_round,
                        instance_name,
                        f"{federated_operator}.tar",
                    ),
                ),
            }
        return minio_urls


# https://www.peterbe.com/plog/best-practice-with-retries-with-requests
# https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
def requests_retry_session(
    retries=3,
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


def get_utc_timestamp():
    dt = datetime.datetime.now(timezone.utc).replace(microsecond=0)
    utc_time = dt.replace(tzinfo=timezone.utc)
    return utc_time


def get_dag_list(
    only_dag_names: bool = True,
    filter_allowed_dags: list = None,
    kind_of_dags: str = "all",
):
    """
    Return a dictionary of airflow DAGs with meta information or a list of DAG ids.

    :param: only_dag_names: If True return a list of DAG ids.
    :param: filter_allowed_dags: None or a list of DAG ids, that are returned exclusively, if they exist in Airflow. If None apply no filter.
    :param: kind_of_dags: One of ['all', 'minio', 'dataset','import']. If 'minio' or 'dataset' only include DAGs with specific properties in the ui-form. If 'import' include only DAGs with tag 'import'.
    """
    if kind_of_dags not in ["all", "minio", "dataset", "import"]:
        raise HTTPException(
            "kind_of_dags must be one of ['all', 'minio', 'dataset','import']"
        )

    with CachedSession(
        "kaapana_cache", expire_after=5, stale_if_error=True, use_temp=True
    ) as s:
        r = requests_retry_session(session=s, retries=1).get(
            f"http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/getdags",
            timeout=TIMEOUT,
        )
    raise_kaapana_connection_error(r)
    raw_dags = r.json()

    dags = {}
    for dag, dag_data in raw_dags.items():
        if "ui_visible" in dag_data and dag_data["ui_visible"] is True:
            if kind_of_dags == "all":
                dags[dag] = dag_data
            elif (kind_of_dags == "dataset") and (
                "ui_forms" in dag_data
                and "data_form" in dag_data["ui_forms"]
                and "properties" in dag_data["ui_forms"]["data_form"]
                and "dataset_name" in dag_data["ui_forms"]["data_form"]["properties"]
            ):
                dags[dag] = dag_data
            elif (kind_of_dags == "minio") and (
                "ui_forms" in dag_data
                and "data_form" in dag_data["ui_forms"]
                and "properties" in dag_data["ui_forms"]["data_form"]
                and "bucket_name" in dag_data["ui_forms"]["data_form"]["properties"]
            ):
                dags[dag] = dag_data
            elif (kind_of_dags == "minio") and (
                "ui_forms" in dag_data
                and "data_form" in dag_data["ui_forms"]
                and "properties" in dag_data["ui_forms"]["data_form"]
                and "bucket_name" in dag_data["ui_forms"]["data_form"]["properties"]
            ):
                dags[dag] = dag_data
            elif kind_of_dags in dag_data.get("tags", []):
                dags[dag] = dag_data

    if only_dag_names is True:
        return sorted(list(dags.keys()))
    else:
        if filter_allowed_dags is None:
            return dags
        elif filter_allowed_dags:
            return {dag: dags[dag] for dag in filter_allowed_dags if dag in dags}
        else:
            return {}


def check_dag_id_and_dataset(
    db_client_kaapana, conf_data, dag_id, owner_kaapana_instance_name
):
    if (
        owner_kaapana_instance_name is not None
        and db_client_kaapana.instance_name != owner_kaapana_instance_name
    ):
        if dag_id not in db_client_kaapana.allowed_dags:
            return f"Dag {dag_id} is not allowed to be triggered from remote!"
        if "data_form" in conf_data:
            pass
            # ToDo adapt!
            # queried_data = crud.get_datasets(conf_data["opensearch_form"])
            # if not queried_data or (not all([bool(set(d) & set(db_client_kaapana.allowed_datasets)) for d in queried_data])):
            #     return f"Queried series with tags " \
            #         f"{', '.join(sorted(list(set([d for item in queried_data for d in item]))))} are not all part of allowed datasets:" \
            #         f"{', '.join(db_client_kaapana.allowed_datasets)}!"
    return None


def execute_job_airflow(conf_data, db_job):
    with requests.Session() as s:
        resp = requests_retry_session(session=s).post(
            f"http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/trigger/{db_job.dag_id}",
            timeout=TIMEOUT,
            json={
                "conf": {
                    **conf_data,
                }
            },
        )
    raise_kaapana_connection_error(resp)
    return resp


def abort_job_airflow(dag_id, dag_run_id, status="failed"):
    with requests.Session() as s:
        resp = requests_retry_session(session=s).post(
            f"http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/abort/{dag_id}/{dag_run_id}",
            timeout=TIMEOUT,
            json={
                "dag_id": dag_id,
                "state": status,
                # "state": {
                #     **status,
                # },
            },
        )
    # raise_kaapana_connection_error(resp)
    return resp


def get_dagrun_tasks_airflow(dag_id, dag_run_id):
    with requests.Session() as s:
        resp = requests_retry_session(session=s).post(
            f"http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/get_dagrun_tasks/{dag_id}/{dag_run_id}",
            timeout=TIMEOUT,
            json={
                "dag_id": dag_id,
            },
        )
    raise_kaapana_connection_error(resp)
    return resp


def get_dagrun_details_airflow(dag_id, dag_run_id):
    with requests.Session() as s:
        resp = requests_retry_session(session=s).get(
            f"http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/dagdetails/{dag_id}/{dag_run_id}",
            timeout=TIMEOUT,
        )
    # connection error handled in function call
    # raise_kaapana_connection_error(resp)
    return resp


# def get_dagruns_airflow(status):
#     with requests.Session() as s:
#         resp = requests_retry_session(session=s).post(f'http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/getdagruns',
#                 timeout=TIMEOUT,
#                 json={
#                     'state': status,
#                 })
#     raise_kaapana_connection_error(resp)
#     return resp


# @functools.lru_cache(maxsize=2)
def get_dagruns_airflow(states):
    dagruns_states = []
    for i in range(len(states)):
        status = states[i]
        with requests.Session() as s:
            resp = requests_retry_session(session=s).post(
                f"http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/getdagruns",
                timeout=TIMEOUT,
                json={
                    "state": status,
                },
            )
        raise_kaapana_connection_error(resp)
        dagruns_states.extend(json.loads(resp.text))

    return dagruns_states


def raise_kaapana_connection_error(r):
    if r.history:
        raise HTTPException(
            "You were redirect to the auth page. Your token is not valid!"
        )
    try:
        r.raise_for_status()
    except:
        raise HTTPException(
            f"Something was not okay with your request code {r}: {r.text}!"
        )
