import subprocess
import sys, os
import glob
import json
import pydicom
from datetime import datetime
import requests


batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])


for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    print("calling sub process.....................!")
   
    ipcmd = "/bin/bash -c pytest"
    try:
        resp = subprocess.check_output(ipcmd,shell=True,stderr=subprocess.STDOUT)
        print(resp)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
    

    log_txt_file_path = os.path.join(element_output_dir, "{}.txt".format(os.path.basename(batch_element_dir)))

    with open(log_txt_file_path, "w", encoding='utf-8') as logData:
        logData.write(str(resp))
        print(f' !!!!!!!!!!!!!  Response is written to {log_txt_file_path}  !!!!!!!!!!!!!!!!')
        


print(' !!!!!!!!!!!!!  Process Completed  !!!!!!!!!!!!!!!!')


"""import subprocess
import sys
print("calling sub process..!")
#resp = subprocess.check_output(["/bin/bash", "-c","pytest > new_outputs.txt"], stderr=subprocess.STDOUT)
resp = subprocess.check_output(["/bin/bash", "-c","pytest"], stderr=subprocess.STDOUT)
print(resp)

print("Completed!")"""