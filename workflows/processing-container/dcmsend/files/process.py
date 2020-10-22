import sys, os
import glob
import subprocess
from datetime import datetime

import pydicom


HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
AETITLE = os.getenv('AETITLE')


def send_dicom_data(send_dir, aetitle=AETITLE):
    try:
        print(f'Sending {send_dir} to {HOST} {PORT} with aetitle {aetitle}')
        dcmsend = subprocess.check_output(
            f'dcmsend -v {HOST} {PORT}  --scan-directories --call {aetitle} --scan-pattern \'*\'  --recurse {send_dir}', stderr=subprocess.STDOUT, shell=True)
        print(dcmsend)
    except subprocess.CalledProcessError as e:
        print(f'No images found in {send_dir}')
    
batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])

    print('Here you find the files you want to work with on a batch element level')
    print(element_input_dir)

    dcm_files = sorted(glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True))

    if len(dcm_files) == 0:
        continue

    dcm_file = dcm_files[0]
    print("dcm-file: {}".format(dcm_file))
    try:
        aetitle = pydicom.dcmread(dcm_file)[0x012, 0x020].value
        print(f'Found aetitle {aetitle}')
    except KeyError:
        aetitle = AETITLE
        print(f'Using default aetitle {aetitle}')

    send_dicom_data(element_input_dir, aetitle)


batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
print(batch_input_dir)
send_dicom_data(batch_input_dir)