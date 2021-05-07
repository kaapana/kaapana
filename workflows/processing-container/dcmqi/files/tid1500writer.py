import sys, os
import glob
import math
import json
import os
import re
import pydicom
from datetime import datetime
import subprocess

DCMQI = '/home/klaus/Downloads/dcmqi-1.2.2-linux-20200602-3efde87/bin/'

# os.environ['BATCH_NAME'] = 'batch'
# os.environ['OPERATOR_IN_DIR'] = 'initial-input'
# os.environ['WORKFLOW_DIR'] = '/home/klaus/private_data/jip-data/dcmqi/nnunet_test-200727123756236842/'
# os.environ['OPERATOR_META_DATA_DIR'] = 'measurement'
# os.environ['OPERATOR_IMAGE_LIBRARY_DIR'] = 'nrrd2dcmsegdev-tid'
# os.environ['OPERATOR_OUT_DIR'] = 'tid1500'
# os.environ['OPERATOR_OUTPUT_DICOM'] = 'test'

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    input_image_library_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IMAGE_LIBRARY_DIR'])
    meta_data_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_META_DATA_DIR'])

    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)
    output_dicom = os.path.join(element_output_dir, f"{os.environ['OPERATOR_OUTPUT_DICOM']}.dcm")
    
    try:
        resp = subprocess.check_output([
            f"{DCMQI}/tid1500writer",
            "--inputCompositeContextDirectory", input_image_library_dir,
            "--inputImageLibraryDirectory", element_input_dir,
            "--inputMetadata", f"{meta_data_dir}/measurement.json",
            "--outputDICOM", output_dicom
        ], stderr=subprocess.STDOUT)
        print(resp)
    except subprocess.CalledProcessError as e:
        print(e.output)
