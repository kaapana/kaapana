import os
import time
from subprocess import PIPE, run

import requests
from kaapanapy.helper import get_project_user_access_token, get_opensearch_client
from kaapanapy.settings import OpensearchSettings
from kaapanapy.logger import get_logger

logger = get_logger(__name__)

ctp_url = os.getenv("CTP_URL", None)
assert ctp_url
dcm_port = "11112"
SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")


def wait_for_opensearch_index(os_client, index):
    """
    Wait until the index was created in opensearch.
    """
    max_tries = 60
    delay = 5
    tries = 0
    index_exists = False
    while not index_exists:
        try:
            index_exists = os_client.indices.exists(index)
            if not index_exists:
                logger.warning(f"{index=} not found in opensearch. Retry ...")
            else:
                return
        except Exception:
            logger.warning("Query to opensearch failed. Retry ...")
        time.sleep(delay)
        tries += 1
        if tries >= max_tries:
            logger.error(f"{index=} not found in opensearch after {tries=}! Exit!")
            exit(1)


def wait_for_file_in_opensearch(os_client, index, series_uid):
    """
    Wait until the series is available in the opensearch index
    """
    queryDict = {}
    queryDict["query"] = {
        "bool": {
            "must": [
                {"match_all": {}},
                {
                    "match_phrase": {
                        "0020000E SeriesInstanceUID_keyword.keyword": {
                            "query": series_uid
                        }
                    }
                },
            ],
            "filter": [],
            "should": [],
            "must_not": [],
        }
    }

    queryDict["_source"] = {}
    max_counter = 60
    counter = 0

    while True:
        counter += 1
        if counter > max_counter:
            logger.error(f"Could not find series in Opensearch in {index=}")
            logger.error(f"counter {counter} > max_counter {max_counter} !")
            exit(1)

        res = os_client.search(index=[index], body=queryDict, size=10000, from_=0)
        hits = res["hits"]["hits"]

        if len(hits) == 1:
            logger.info(f"Found {series_uid=} in {index=}")
            break
        else:
            time.sleep(5)


def send_dicom_data(
    path_to_dicom_files: str, dataset: str = "kp-phantom", project: str = "kp-admin"
):
    """
    Send all dicom files in the directory path_to_dicom_files to the kaapana ctp.
    Assign it to the provided project and add it to the provided dataset.
    """

    if not dataset.startswith("kp-"):
        dataset = "kp-" + dataset
    if not project.startswith("kp-"):
        project = "kp-" + project

    logger.info("Send example files to ctp server.")
    command = [
        "dcmsend",
        "+sd",
        "+r",
        "-v",
        ctp_url,
        dcm_port,
        "-aet",
        dataset,
        "-aec",
        project,
        path_to_dicom_files,
    ]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if output.returncode == 0:
        logger.info("Example file successfully send to the ctp server!")
    else:
        logger.warning("error sending img: {}!".format(path_to_dicom_files))
        logger.warning(output.stdout)
        logger.warning(output.stderr)


def wait_for_file_in_pacs(study_uid, access_token, max_counter=60):
    """
    Wait until the study with stuidy_uid is available in the PACS.
    """
    counter = 0
    dcmweb_endpoint = f"http://dicom-web-filter-service.{SERVICES_NAMESPACE}.svc:8080"
    while counter < max_counter:
        r = requests.get(
            f"{dcmweb_endpoint}/studies",
            verify=False,
            params={"StudyInstanceUID": study_uid},
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )
        r.raise_for_status()
        if r.status_code != 200:
            counter += 1
            logger.warning(f"Example file not found in PACS! Retry ...")
            time.sleep(5)
        else:
            logger.info("Example file found in PACs")
            return True
    return False


if __name__ == "__main__":
    admin_project = "admin"
    project_index = OpensearchSettings().default_index

    access_token = None
    for i in range(10):
        try:
            access_token = get_project_user_access_token()
            break
        except KeyError:
            logger.warning(
                "Receiving the access token for the system user failed. Retry..."
            )
            time.sleep(10)
    if not access_token:
        raise KeyError(
            "Could not receive an access token for the system user from Keycloak."
        )
    os_client = get_opensearch_client(access_token=access_token)

    wait_for_opensearch_index(os_client=os_client, index=project_index)
    send_dicom_data(
        path_to_dicom_files="/dicom_test_data/phantom",
        dataset="phantom",
        project=admin_project,
    )
    example_phantom_send = {
        "study_uid": "1.3.12.2.1107.5.1.4.73104.30000020081307472119600000009",
        "series_uid": "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735",
    }

    wait_for_file_in_pacs(
        study_uid=example_phantom_send["study_uid"], access_token=access_token
    )

    wait_for_file_in_opensearch(
        os_client=os_client,
        index=project_index,
        series_uid=example_phantom_send["series_uid"],
    )
