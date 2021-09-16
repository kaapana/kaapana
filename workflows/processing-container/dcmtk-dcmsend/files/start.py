import os
import glob
import time
from subprocess import PIPE, run
import pydicom
import requests
from pathlib import Path

HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
HTTP_PORT = os.getenv("HTTP_PORT","8080")
AETITLE = os.getenv('AETITLE', 'NONE')
AETITLE = None if AETITLE == "NONE" else AETITLE
LEVEL = os.getenv('LEVEL', 'element')

check_arrival = os.getenv("CHECK_ARRIVAL", "False")
check_arrival = True if check_arrival.lower() == "true" else False

print(f"Proxy http: {os.getenv('http_proxy')}")
print(f"Proxy https: {os.getenv('https_proxy')}")
print(f"AETITLE: {AETITLE}")
print(f"LEVEL: {LEVEL}")

dicom_sent_count = 0


def send_dicom_data(send_dir, aetitle=AETITLE, check_arrival=False, timeout=60):
    global dicom_sent_count

    def check_if_arrived(seriesUID):
        print("#")
        print("############### Check if DICOMs arrived ###############")
        print("#")
        max_tries = 30
        tries = 0

        while tries < max_tries:
            pacs_dcmweb_endpoint = f"http://{HOST}:{HTTP_PORT}/dcm4chee-arc/aets/KAAPANA/rs/instances"

            payload = {
                'SeriesInstanceUID': seriesUID
            }
            print("#")
            print(f"# request: {pacs_dcmweb_endpoint}: {payload}")
            print("#")
            httpResponse = requests.get(pacs_dcmweb_endpoint, params=payload, timeout=2)
            if httpResponse.status_code == 200:
                print("# Series found -> success !")
                break
            else:
                print("# Series not found -> sleep 2s !")
                tries += 1
                time.sleep(2)

        print("#")
        print("# Done")
        print("#")
        if tries >= max_tries:
            print("# -> too many failed requests -> Error!")
            print("# ABORT")
            return False
        else:
            return True

    dicom_list = list(Path(send_dir).rglob('*.dcm'))
    dcm_file = pydicom.dcmread(dicom_list[0])
    series_uid = str(dcm_file[0x0020, 0x000E].value)

    print(f'Found series_uid {series_uid}')
    if aetitle is None:
        if len(dicom_list) == 0:
            print(send_dir)
            print("############### no dicoms found...!")
            raise FileNotFoundError
        try:
            aetitle = str(dcm_file[0x012, 0x020].value)
            print(f'Found aetitle    {aetitle}')
        except Exception as e:
            print(f'Could not load aetitle: {e}')
            aetitle = "KAAPANA export"
            print(f'Using default aetitle {aetitle}')

    print(f'Sending {send_dir} to {HOST} {PORT} with aetitle {aetitle}')
    # To process even if the input contains non-DICOM files the --no-halt option is needed (e.g. zip-upload functionality)
    command = ['dcmsend', '-v', f'{HOST}', f'{PORT}', '-aet', 'kaapana', '-aec', f'{aetitle}', '--scan-directories', '--no-halt', '--recurse', f'{send_dir}']
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)
    if output.returncode != 0 or "with status SUCCESS" not in str(output):
        print("############### Something went wrong with dcmsend!")
        for line in str(output).split("\\n"):
            print(line)
        print("##################################################")
        exit(1)
    else:
        print(f"Success! output: {output}")
        print("")

    if check_arrival and not check_if_arrived(seriesUID=series_uid):
        print(f"Arrival check failed!")
        exit(1)

    dicom_sent_count += 1


if LEVEL == 'element':
    batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

    for batch_element_dir in batch_folders:

        element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
        print(element_input_dir)

        dcm_files = sorted(glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True))

        if len(dcm_files) == 0:
            continue

        dcm_file = dcm_files[0]
        print("dcm-file: {}".format(dcm_file))

        send_dicom_data(element_input_dir, check_arrival=check_arrival, timeout=600)

elif LEVEL == 'batch':
    batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
    print(f"Sending DICOM data from batch-level: {batch_input_dir}")
    send_dicom_data(batch_input_dir, check_arrival=check_arrival, timeout=3600)
else:
    raise NameError('level must be either "element" or "batch". \
        If batch, an operator folder next to the batch folder with .dcm files is expected. \
        If element, *.dcm are expected in the corresponding operator with .dcm files is expected.'
                    )

if dicom_sent_count == 0:
    print("##################################################")
    print("#")
    print("############### Something went wrong!")
    print("# --> no DICOM sent !")
    print("# ABORT")
    print("#")
    print("##################################################")
    exit(1)
