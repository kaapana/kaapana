import sys, os
import glob
import json
from datetime import datetime

batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

json_list = []
for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    print(element_input_dir)
    json_files = sorted(glob.glob(os.path.join(element_input_dir, "*.json*"), recursive=True))

    if len(json_files) == 0:
        print("No json file found!")
        exit(1)
    else:
        print("Pooling jsons")
    
        for json_path in json_files:
            with open(json_path, 'r') as f:
                json_dict = json.load(f)
                print('json_dict', json_dict)
                json_list.append(json_dict)

batch_output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])
if not os.path.exists(batch_output_dir):
    os.makedirs(batch_output_dir)

json_file_path = os.path.join(batch_output_dir, "pooled_json_{}.json".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')))

with open(json_file_path, "w", encoding='utf-8') as jsonData:
    json.dump(json_list, jsonData)
