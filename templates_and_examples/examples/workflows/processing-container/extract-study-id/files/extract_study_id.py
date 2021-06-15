import sys, os
import glob
import json
import pydicom
from datetime import datetime

# For local testng

# os.environ["WORKFLOW_DIR"] = "<your data directory>"
# os.environ["BATCH_NAME"] = "batch"
# os.environ["OPERATOR_IN_DIR"] = "initial-input"
# os.environ["OPERATOR_OUT_DIR"] = "output"

# From the template
batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    # The processing algorithm
    print(f'Checking {element_input_dir} for dcm files and writing results to {element_output_dir}')
    dcm_files = sorted(glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True))

    if len(dcm_files) == 0:
        print("No dicom file found!")
        exit(1)
    else:
        print(("Extracting study_id: %s" % dcm_files))

        incoming_dcm = pydicom.dcmread(dcm_files[0])
        json_dict = {
            'study_id': incoming_dcm.StudyInstanceUID,
            'series_uid': incoming_dcm.SeriesInstanceUID
        }

        if not os.path.exists(element_output_dir):
            os.makedirs(element_output_dir)

        json_file_path = os.path.join(element_output_dir, "{}.json".format(os.path.basename(batch_element_dir)))

        with open(json_file_path, "w", encoding='utf-8') as jsonData:
            json.dump(json_dict, jsonData, indent=4, sort_keys=True, ensure_ascii=True)
