import subprocess
import sys, os
import glob
import json
import pydicom
from datetime import datetime

#resp = subprocess.check_output(["/bin/bash", "-c","pytest > new_outputs.txt"], stderr=subprocess.STDOUT)

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    # The processing algorithm
    
    #dcm_files = sorted(glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True))

    #if len(dcm_files) == 0:
        #print("No dicom file found!")
        #exit(1)
    #else:
        #print(("Extracting study_id: %s" % dcm_files))

        #incoming_dcm = pydicom.dcmread(dcm_files[0])
        #json_dict = {
            #'study_id': incoming_dcm.StudyInstanceUID,
            #'series_uid': incoming_dcm.SeriesInstanceUID
        #}

    #if not os.path.exists(element_output_dir):
        #os.makedirs(element_output_dir)
    print("calling sub process....................!")
    resp = subprocess.check_output(["/bin/bash", "-c","pytest"], stderr=subprocess.STDOUT)
    print(resp)

    log_txt_file_path = os.path.join(element_output_dir, "{}.log".format(os.path.basename(batch_element_dir)))

    with open(log_txt_file_path, "w", encoding='utf-8') as logData:
        logData.write(resp)
        print(f' !!!!!!!!!!!!!  Response is written to {log_txt_file_path}  !!!!!!!!!!!!!!!!')
        


print(' !!!!!!!!!!!!!  Process Completed  !!!!!!!!!!!!!!!!')