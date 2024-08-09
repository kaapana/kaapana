import glob
import json
import os
import shutil
import time
from subprocess import PIPE, run

import pydicom
import requests
from kaapanapy.helper import get_project_user_access_token, get_opensearch_client
from kaapanapy.settings import OpensearchSettings
from kaapanapy.logger import get_logger

logger = get_logger(__name__)

tmp_data_dir = "/slow_data_dir/TMP"
ctp_url = os.getenv("CTP_URL", None)
assert ctp_url
dcm_port = "11112"
os_host = os.getenv("OPENSEARCH_HOST", None)
assert os_host
os_port = os.getenv("OPENSEARCH_PORT", "9200")
assert os_port
airflow_host = os.getenv("AIRFLOW_TRIGGER", None)
assert airflow_host
example_files = os.getenv("EXAMPLE", "/example/Winfried_phantom.zip")
SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")

index = OpensearchSettings().default_index

access_token = get_project_user_access_token()
os_client = get_opensearch_client(access_token=access_token)

### Wait for opensearch index to be created


def wait_for_opensearch_index():
    """
    Wait until the index was created in opensearch.
    """
    max_tries = 60
    delay = 5
    tries = 0
    while not os_client.indices.exists(index):
        tries += 1
        logger.warning(f"{index=} not found in opensearch. Retry ...")
        if tries >= max_tries:
            logger.error(f"{index=} not found in opensearch after {tries=}! Exit!")
            exit(1)
        time.sleep(delay)


def send_file():
    files_sent = 0
    max_count = 10
    counter = 0
    if os.path.exists(tmp_data_dir):
        logger.info("Found existing dicom data!")
        while counter < max_count:
            dcm_dirs = []
            counter += 1

            file_list = glob.glob(tmp_data_dir + "/**/*", recursive=True)
            for fi in file_list:
                if os.path.isfile(fi):
                    dcm_dirs.append(os.path.dirname(fi))
            dcm_dirs = list(set(dcm_dirs))

            logger.debug("Files found: {}".format(len(file_list)))
            logger.debug("Dcm dirs found: {}".format(len(dcm_dirs)))
            if len(dcm_dirs) == 0:
                logger.debug("Delete TMP dir!")
                shutil.rmtree(tmp_data_dir)
                break

            for dcm_dir in dcm_dirs:
                try:
                    dcm_file = os.path.join(dcm_dir, os.listdir(dcm_dir)[0])
                    logger.debug("dcm-file: {}".format(dcm_file))
                    dataset = pydicom.dcmread(dcm_file)[0x0012, 0x0020].value

                    command = [
                        "dcmsend",
                        "+sd",
                        "+r",
                        "-v",
                        ctp_url,
                        dcm_port,
                        "-aet",
                        "re-index",
                        "-aec",
                        dataset,
                        dcm_dir,
                    ]
                    # output = run(command)
                    output = run(
                        command, stdout=PIPE, stderr=PIPE, universal_newlines=True
                    )
                    if output.returncode == 0:
                        files_sent += 1
                        shutil.rmtree(dcm_dir)
                    else:
                        logger.error("Sending img: {} failed!".format(dcm_dir))
                        logger.error(output.stdout)
                        logger.error(output.stderr)
                        raise
                except Exception as e:
                    logger.warning("Error while sending dcm... ")
                    logger.warning(str(e))
                    error_dcm_path = dcm_dir.replace("TMP", "TMP_ERROR")
                    logger.debug("Moving data to {}".format(error_dcm_path))
                    if not os.path.exists(error_dcm_path):
                        os.makedirs(error_dcm_path)
                    shutil.move(dcm_dir, error_dcm_path)

            if counter >= max_count:
                logger.warning("Max count of loops exceeded!")
                logger.debug("Sent dicoms: {}".format(files_sent))
                exit(0)

        logger.debug("Sent dicoms: {}".format(files_sent))


# first file will init meta


def send_meta_init():
    logger.info("Send Dicom init meta image....")
    command = [
        "dcmsend",
        "+sd",
        "+r",
        "-v",
        ctp_url,
        dcm_port,
        "-aet",
        "dicom-test",
        "-aec",
        "dicom-test",
        "/dicom_test_data/init_data",
    ]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if output.returncode == 0:
        logger.info("Push init meta dicom -> success")
        example_file_list = glob.glob(
            "/dicom_test_data/init_data" + "/*.dcm", recursive=True
        )
        examples_send = []
        for examples in example_file_list:
            item = dict()
            item["study_uid"] = pydicom.dcmread(examples)[0x0020, 0x000D].value
            item["series_uid"] = pydicom.dcmread(examples)[0x0020, 0x000E].value
            item["instance_uid"] = pydicom.dcmread(examples)[0x0008, 0x0018].value
            item["modality"] = pydicom.dcmread(examples)[0x0008, 0x0060].value
            examples_send.append(item)
        return examples_send
    else:
        logger.error("Sending example dicom failed!")
        logger.error(output.stdout)
        logger.error(output.stderr)
        exit(1)


def check_file_on_platform(examples_send):
    for file in examples_send:
        max_counter = 60
        counter = 0
        quido_success = wait_for_file_in_pacs(file)
        if not quido_success:
            logger.error("File not found in PACs!")
            exit(1)
        meta_query_success = False
        while True:
            if counter > max_counter:
                logger.error("# Could not find series in META!")
                logger.error(f"# counter {counter} > max_counter {max_counter} !")
                exit(1)

            queryDict = {}
            queryDict["query"] = {
                "bool": {
                    "must": [
                        {"match_all": {}},
                        {
                            "match_phrase": {
                                "0020000E SeriesInstanceUID_keyword.keyword": {
                                    "query": file["series_uid"]
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
            try:
                res = os_client.search(
                    index=[index], body=queryDict, size=10000, from_=0
                )
            except Exception as e:
                logger.warning(f"Could not request Opensearch! Error: {str(e)}")
                counter += 1
                time.sleep(10)
                continue
            hits = res["hits"]["hits"]
            logger.debug(("GOT %s results, wait and retry!" % len(hits)))
            if len(hits) == 1:
                meta_query_success = True
                break
            else:
                counter += 1
                time.sleep(5)
        if not meta_query_success:
            logger.warning("File not found in META!")
            exit(0)


def trigger_delete_dag(examples_send):
    for file in examples_send:
        headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
        }

        conf = {
            "data_form": {"identifiers": [file["series_uid"]]},
            "workflow_form": {
                "delete_complete_study": False,
                "single_execution": False,
            },
            "form_data": {"username": "system"},
        }
        dag_id = "delete-series-from-platform"
        logger.debug("trigger url: {}/{}".format(airflow_host, dag_id))
        dump = json.dumps(conf)
        response = requests.post(
            "{}/{}".format(airflow_host, dag_id),
            headers=headers,
            data=dump,
            verify=False,
        )

        if response.status_code == requests.codes.ok:
            logger.debug("Delete example dicom sucessful triggered")
        else:
            logger.warning("Error response: %s !" % response.status_code)
            logger.warning(response.content)


def send_example_file_to_ctp():
    logger.info("Send example files to ctp server.")
    example_dir = "/dicom_test_data/phantom"
    command = [
        "dcmsend",
        "+sd",
        "+r",
        "-v",
        ctp_url,
        dcm_port,
        "-aet",
        "phantom-example",
        "-aec",
        "phantom-example",
        example_dir,
    ]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if output.returncode == 0:
        logger.info("Example file successfully send to the ctp server!")
    else:
        logger.warning("error sending img: {}!".format(example_dir))
        logger.warning(output.stdout)
        logger.warning(output.stderr)


def wait_for_file_in_pacs(file, max_counter=60):
    """
    Wait until the
    """
    access_token = get_project_user_access_token()
    counter = 0
    dcmweb_endpoint = f"http://dicom-web-filter-service.{SERVICES_NAMESPACE}.svc:8080"
    while counter < max_counter:
        r = requests.get(
            f"{dcmweb_endpoint}/studies",
            verify=False,
            params={"StudyInstanceUID": file["study_uid"]},
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-forwarded-access-token": access_token,
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
    init_meta_file = send_meta_init()
    wait_for_opensearch_index()
    check_file_on_platform(examples_send=init_meta_file)
    trigger_delete_dag(examples_send=init_meta_file)
    send_file()  ### This function does nothing, if tmp_data_dir is not an existing path
    send_example_file_to_ctp()
    example_phantom_send = [
        {
            "study_uid": "1.3.12.2.1107.5.1.4.73104.30000020081307472119600000009",
            "series_uid": "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735",
        }
    ]
    check_file_on_platform(examples_send=example_phantom_send)
