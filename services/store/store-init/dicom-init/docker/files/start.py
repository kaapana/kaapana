import os
import shutil
import pydicom
import requests
import time
import glob
import subprocess
import json
from zipfile import ZipFile
from subprocess import PIPE, run
from opensearchpy import OpenSearch

tmp_data_dir = "/slow_data_dir/TMP"
ctp_url = os.getenv("CTP_URL", None)
assert ctp_url
dcm_port = "11112"
dcm4chee_host = os.getenv("DCM4CHEE", None)
assert dcm4chee_host
aet = os.getenv("AET", "KAAPANA")
os_host = os.getenv("OPENSEARCH_HOST", None)
assert os_host
os_port = os.getenv("OPENSEARCH_PORT", "9200")
assert os_port
airflow_host = os.getenv("AIRFLOW_TRIGGER", None)
assert airflow_host
example_files = os.getenv("EXAMPLE", "/example/Winfried_phantom.zip")

index = "meta-index"
auth = None
# auth = ('admin', 'admin') # For testing only. Don't store credentials in code.

os_client = OpenSearch(
    hosts=[{'host': os_host, 'port': os_port}],
    http_compress=True,  # enables gzip compression for request bodies
    http_auth=auth,
    # client_cert = client_cert_path,
    # client_key = client_key_path,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
    timeout=2,
    # ca_certs = ca_certs_path
)


def send_file():
    files_sent = 0
    max_count = 10
    counter = 0
    if os.path.exists(tmp_data_dir):
        print("Found existing dicom data!")
        while counter < max_count:
            dcm_dirs = []
            counter += 1

            file_list = glob.glob(tmp_data_dir + "/**/*", recursive=True)
            for fi in file_list:
                if os.path.isfile(fi):
                    dcm_dirs.append(os.path.dirname(fi))
            dcm_dirs = list(set(dcm_dirs))

            print("Files found: {}".format(len(file_list)))
            print("Dcm dirs found: {}".format(len(dcm_dirs)))
            if len(dcm_dirs) == 0:
                print("Delete TMP dir!")
                shutil.rmtree(tmp_data_dir)
                break

            for dcm_dir in dcm_dirs:
                try:
                    dcm_file = os.path.join(dcm_dir, os.listdir(dcm_dir)[0])
                    print("dcm-file: {}".format(dcm_file))
                    dataset = pydicom.dcmread(dcm_file)[0x0012, 0x0020].value

                    command = ["dcmsend", "+sd", "+r", "-v", ctp_url, dcm_port, "-aet", "re-index", "-aec", dataset,
                               dcm_dir]
                    # output = run(command)
                    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
                    if output.returncode == 0:
                        files_sent += 1
                        print("############################ success: {}".format(files_sent))
                        shutil.rmtree(dcm_dir)
                    else:
                        print("error sending img: {}!".format(dcm_dir))
                        print(
                            "############################################################################################################## STDOUT:")
                        print(output.stdout)
                        print(
                            "############################################################################################################## STDERR:")
                        print(output.stderr)
                        raise
                except Exception as e:
                    print(e)
                    error_dcm_path = dcm_dir.replace("TMP", "TMP_ERROR")
                    print("Error while sending dcm... ")
                    print("Moving data to {}".format(error_dcm_path))
                    if not os.path.exists(error_dcm_path):
                        os.makedirs(error_dcm_path)
                    shutil.move(dcm_dir, error_dcm_path)

            if counter >= max_count:
                print("------------------------------------------------------------------> Max loops exception!")
                print("Sent dicoms: {}".format(files_sent))
                exit(0)

        print("Sent dicoms: {}".format(files_sent))

# first file will init meta


def send_meta_init():
    print("Send Dicom init meta image....")
    print("")
    command = ["dcmsend", "+sd", "+r", "-v", ctp_url, dcm_port, "-aet", "dicom-test", "-aec", "dicom-test", "/dicom_test_data/init_data"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if output.returncode == 0:
        print("############################ Push init meta dicom -> success")
        example_file_list = glob.glob("/dicom_test_data/init_data" + "/*.dcm", recursive=True)
        examples_send = []
        for examples in example_file_list:
            item = dict()
            item['study_uid'] = pydicom.dcmread(examples)[0x0020, 0x000D].value
            item['series_uid'] = pydicom.dcmread(examples)[0x0020, 0x000E].value
            item['instance_uid'] = pydicom.dcmread(examples)[0x0008, 0x0018].value
            item['modality'] = pydicom.dcmread(examples)[0x0008, 0x0060].value
            examples_send.append(item)
        return examples_send
    else:
        print("error sending example dicom!")
        print(
            "############################################################################################################## STDOUT:")
        print(output.stdout)
        print(
            "############################################################################################################## STDERR:")
        print(output.stderr)
        exit(1)


def check_file_on_platform(examples_send):
    for file in examples_send:
        max_counter = 100
        counter = 0
        quido_success = False
        while counter < max_counter:
            # quido file
            r = requests.get(f"{dcm4chee_host}/dcm4chee-arc/aets/{aet}/rs/studies/{file['study_uid']}/series/{file['series_uid']}/instances", verify=False)
            if r.status_code != requests.codes.ok:
                counter += 1
                time.sleep(10)
            else:
                quido_success = True
                print("File successfully found in PACs")
                break
        if not quido_success:
            print("File not found in PACs!")
            exit(1)
        max_counter = 20
        counter = 0
        meta_query_success = False
        while True:
            if counter > max_counter:
                print("# Could not find series in META!")
                print(f"# counter {counter} > max_counter {max_counter} !")
                exit(1)


            queryDict = {}
            queryDict["query"] = {'bool': {
                'must':
                    [
                        {'match_all': {}},
                        {'match_phrase': {
                            '0020000E SeriesInstanceUID_keyword.keyword': {'query': file['series_uid']}}},
                    ], 'filter': [], 'should': [], 'must_not': []}}

            queryDict["_source"] = {}
            try:
                res = os_client.search(index=[index], body=queryDict, size=10000, from_=0)
            except Exception as e:
                print("Could not request Opensearch! Error:")
                print(e)
                counter += 1
                time.sleep(10)

            hits = res['hits']['hits']
            print(("GOT %s results, wait and retry!" % len(hits)))
            if len(hits) == 1:
                meta_query_success = True
                break
            else:
                counter += 1
                time.sleep(5)
        if not meta_query_success:
            print("File not found in META!")
            exit(0)


def trigger_delete_dag(examples_send):
    for file in examples_send:

        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
        }

        conf = {
            "data_form": {
                "cohort_identifiers": [
                    file['series_uid']
                ],
                "cohort_query": {
                    'index': 'meta-index'
                }
            },
            "workflow_form": {
                "delete_complete_study": False,
                "single_execution": False
            }
        }
        dag_id = "delete-series-from-platform"
        print("data", conf)
        print("trigger url: ", '{}/{}'.format(airflow_host, dag_id))
        dump = json.dumps(conf)
        response = requests.post('{}/{}'.format(airflow_host, dag_id), headers=headers,data=dump, verify=False)
        
        if response.status_code == requests.codes.ok:
            print("Delete example dicom sucessful triggered")
        else:
            print("Error response: %s !" % response.status_code)
            print(response.content)


def send_example():
    print("Unzipping example files")
    example_dir = "/dicom_test_data/phantom"
    command = ["dcmsend", "+sd", "+r", "-v", ctp_url, dcm_port, "-aet", "phantom-example", "-aec", "phantom-example", example_dir]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if output.returncode == 0:
        print("############################ success send example")
    else:
        print("error sending img: {}!".format(example_dir))
        print(
            "############################################################################################################## STDOUT:")
        print(output.stdout)
        print(
            "############################################################################################################## STDERR:")
        print(output.stderr)


if __name__ == "__main__":
    print("Started dicom init script...")
    print("Fail protection enabled...")
    init_meta_file = send_meta_init()
    check_file_on_platform(examples_send=init_meta_file)
    trigger_delete_dag(examples_send=init_meta_file)
    send_file() ### This function does nothing, if tmp_data_dir is not an existing path
    send_example()
    example_phantom_send = [
        {"study_uid": "1.3.12.2.1107.5.1.4.73104.30000020081307472119600000009",
        "series_uid":"1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"}
        ]
    check_file_on_platform(examples_send=example_phantom_send)

