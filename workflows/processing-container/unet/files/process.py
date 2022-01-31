import sys, os
import shutil
import glob
from distutils.dir_util import copy_tree

batch_output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])
if not os.path.exists(batch_output_dir):
    os.makedirs(batch_output_dir)

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for idx, batch_element_dir in enumerate(batch_folders):
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])

    print('Here you find the files you want to work with on a batch element level')
    print(element_input_dir)
    target_dir = os.path.join(batch_output_dir, str(idx))
    os.makedirs(target_dir, exist_ok=True)
    copy_tree(element_input_dir, target_dir)

