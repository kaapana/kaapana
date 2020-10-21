import sys, os
import glob
from datetime import datetime

batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])

    print('Here you find the files you want to work with on a batch element level')
    print(element_input_dir)

    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    print('Here you should write the files that you generate on a batch element level')
    print(element_output_dir)


batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
print('Here you find the files you want to work with on a batch level')
print(batch_input_dir)

batch_output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])
if not os.path.exists(batch_output_dir):
    os.makedirs(batch_output_dir)
print('Here you should write the files that you generate on a batch level')
print(batch_output_dir)