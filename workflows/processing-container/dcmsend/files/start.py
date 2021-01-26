import sys
import os
import glob
from subprocess import PIPE, run
import pydicom
from pathlib import Path

HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
AETITLE = os.getenv('AETITLE')
LEVEL = os.getenv('LEVEL', 'element')
print(f"Proxy http: {os.getenv('http_proxy')}")
print(f"Proxy https: {os.getenv('https_proxy')}")

dicom_sent_count = 0


def send_dicom_data(send_dir, aetitle=AETITLE, timeout=60):
    global dicom_sent_count

    if not list(Path(send_dir).rglob('*.dcm')):
        print(send_dir)
        print("############### no dicoms found...!")
        raise FileNotFoundError
    print(f'Sending {send_dir} to {HOST} {PORT} with aetitle {aetitle}')
    command = ['dcmsend', '-v', f'{HOST}', f'{PORT}', '-aet', 'kaapana', '-aec', f'{aetitle}', '--scan-directories', '--recurse', f'{send_dir}']
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)
    if output.returncode != 0:
        print("############### Something went wrong with dcmsend!")
        for line in str(output).split("\\n"):
            print(line)
        print("##################################################")
        exit(1)
    else:
        print(f"Success! output: {output}")
        print("")
    dicom_sent_count += 1


if LEVEL == 'element':
    batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

    for batch_element_dir in batch_folders:

        element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
        print(element_input_dir)

        dcm_files = sorted(glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True))

        if len(dcm_files) == 0:
            continue

        dcm_file = dcm_files[0]
        print("dcm-file: {}".format(dcm_file))
        try:
            aetitle = pydicom.dcmread(dcm_file)[0x012, 0x020].value
            print(f'Found aetitle {aetitle}')
        except Exception as e:
            print(f'Could not load aetitle: {e}')
            aetitle = AETITLE
            print(f'Using default aetitle {aetitle}')
        send_dicom_data(element_input_dir, aetitle)
elif LEVEL == 'batch':
    batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
    print(f"Sending DICOM data from batch-level: {batch_input_dir}")
    send_dicom_data(batch_input_dir, timeout=3600)
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
