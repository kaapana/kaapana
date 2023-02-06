import os
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
import json

import torch
import monai
from monai.bundle import ConfigParser 
from monai.data import decollate_batch

# For multiprocessing -> usually you should scale via multiple containers!
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run
execution_timeout=10
 
# # Counter to check if smth has been processed
# processed_count = 0
# 
# # MONAI inference process
# def process_input_file(filepath): 
#     global processed_count
#     
#     meta_file_path = os.path.join(os.environ["monai_workspace_model_dir"], "configs/metadata.json")
#     config_file_path = os.path.join(os.environ["monai_workspace_model_dir"], "configs/inference.json")
#     
#     command = f"python -m monai.bundle run evaluating --meta_file {meta_file_path} --config_file {config_file_path}"
#     output = run(command, capture_output=True, universal_newlines=True, timeout=execution_timeout, shell=True)
#     stdout = output.stdout.strip()
#     stderr = output.stderr.strip()
#     print(stdout)
#     print(stderr)
# 
#     processed_count += 1
#     return True, filepath


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None
# workflow_dir = "data"

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None
# batch_name = "batch"

# operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
# operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
# assert operator_in_dir is not None
# # operator_in_dir = "dcm-converter"

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None
# operator_out_dir = "monai-inference"

boolean_var = getenv("SOME_BOOLEAN_VAR", "False")
boolean_var = True if boolean_var.lower() == "true" else False

monai_data_input_bucket = getenv("MONAI_DATA_INPUT_BUCKET", "None")
monai_data_input_bucket = monai_data_input_bucket if monai_data_input_bucket.lower() != "none" else None
assert monai_data_input_bucket is not None
operator_in_dir = monai_data_input_bucket

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

# How many processes should be started?
parallel_processes = 3

### MONAI inference specific global vars
# model_dir
monai_task_n_version = "spleen_ct_segmentation_v0.3.7"    # TODO: get as input
monai_task = "spleen_ct_segmentation"
model_dir = os.path.join("/models/MONAI", monai_task_n_version)
# model_dir = "models/MONAI/spleen_ct_segmentation_v0.3.7"
# GPU device
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# os.environ["monai_workspace"] = "/home/m391k/kaapana/models/MONAI/spleen_ct_segmentation_v0.3.7"
os.environ["monai_workspace"] = "/models/MONAI/spleen_ct_segmentation_v0.3.7"
os.environ["monai_workspace_eval"] = os.path.join(os.environ["monai_workspace"], "eval/")
# os.environ["monai_workspace_dataset"] = "/home/m391k/kaapana/data/batch/10.1.2.3.4.5.6.2222.4.44.44.4/dcm-converter" # os.path.join(os.environ["monai_workspace"], "dataset/")
# os.environ["monai_workspace_dataset"] = os.path.join("/", workflow_dir, batch_name)
os.environ["monai_workspace_dataset"] = os.path.join("/", "monai", monai_data_input_bucket)
os.environ["monai_workspace_model_dir"] = os.path.join(os.environ["monai_workspace"], "spleen_ct_segmentation")
os.environ["monai_workspace_model_path"] = os.path.join(os.environ["monai_workspace_model_dir"], "models", "model.pt")
Path(os.environ["monai_workspace_eval"]).mkdir(parents=True, exist_ok=True)

inference_json = json.load(open(os.environ["monai_workspace_model_dir"] + "/configs/inference.json"))
#setup variables
inference_json["bundle_root"] = os.environ["monai_workspace"]
inference_json["output_dir"] = os.environ["monai_workspace_eval"]
inference_json["dataset_dir"] = os.environ["monai_workspace_dataset"]
inference_json["handlers"][0]["load_path"] = os.environ["monai_workspace_model_path"]
# inference_json["datalist"] = "$list(@dataset_dir + pd.read_csv(@dataset_dir + 'test.csv').t2)"

### MONAI Inference Process:

# gather input files
input_files = glob(join("/minio", monai_data_input_bucket, input_file_extension), recursive=True)
print(f"# Found {len(input_files)} input-files!")

# add datalist to inference.json
inference_json["datalist"] = input_files
with open(os.path.join(os.environ["monai_workspace_model_dir"] + "/configs/inference.json"), 'w') as fp:
    json.dump(inference_json, fp)
config = ConfigParser()
config.read_config(os.path.join(os.environ["monai_workspace_model_dir"] + "/configs/inference.json"))

# Inference
meta_file_path = os.path.join(os.environ["monai_workspace_model_dir"], "configs/metadata.json")
config_file_path = os.path.join(os.environ["monai_workspace_model_dir"], "configs/inference.json")
command = f"python -m monai.bundle run evaluating --meta_file {meta_file_path} --config_file {config_file_path}"
output = run(command, capture_output=True, universal_newlines=True, timeout=execution_timeout, shell=True)
stdout = output.stdout.strip()
stderr = output.stderr.strip()
print(stdout)
print(stderr)

# TODO: write results to output dir

# print("##################################################")
# print("#")
# print(f"# Starting operator {operator_out_dir}:")
# print("#")
# print(f"# workflow_dir:     {workflow_dir}")
# print(f"# batch_name:       {batch_name}")
# print(f"# operator_in_dir:  {operator_in_dir}")
# print(f"# operator_out_dir: {operator_out_dir}")
# print(f"# boolean_var:      {boolean_var}")
# print("#")
# print("##################################################")
# print("#")
# print("# Starting processing on BATCH-ELEMENT-level ...")
# print("#")
# print("##################################################")
# print("#")
# 
# # Loop for every batch-element (usually series)
# # batch_folders = sorted([f for f in glob(join('/', workflow_dir, batch_name, '*'))]) # /home/m391k/kaapana/data
# # batch_folders = sorted([f for f in glob(join('/home/m391k/kaapana/data', batch_name, '*'))])
# batch_folders = sorted([f for f in glob(join(os.path.join("/", "monai", monai_data_input_bucket), '*'))])
# for batch_element_dir in batch_folders:
#     print("#")
#     print(f"# Processing batch-element {batch_element_dir}")
#     print("#")
#     element_input_dir = join(batch_element_dir, operator_in_dir)
#     element_output_dir = join(batch_element_dir, operator_out_dir)
# 
#     # check if input dir present
#     if not exists(element_input_dir):
#         print("#")
#         print(f"# Input-dir: {element_input_dir} does not exists!")
#         print("# -> skipping")
#         print("#")
#         continue
# 
#     # creating output dir
#     Path(element_output_dir).mkdir(parents=True, exist_ok=True)
# 
#     # creating output dir
#     input_files = glob(join(element_input_dir, input_file_extension), recursive=True)
#     print(f"# Found {len(input_files)} input-files!")
# 
#     # MONAI: add datalist to inference.json
#     inference_json["datalist"] = input_files
#     with open(os.path.join(os.environ["monai_workspace_model_dir"] + "/configs/inference.json"), 'w') as fp:
#         json.dump(inference_json, fp)
#     config = ConfigParser()
#     config.read_config(os.path.join(os.environ["monai_workspace_model_dir"] + "/configs/inference.json"))
# 
#     # Single process:
#     # Loop for every input-file found with extension 'input_file_extension'
#     for input_file in input_files:
#         result, input_file = process_input_file(filepath=input_file)
#     
#     # Alternative with multi-processing
#     results = ThreadPool(parallel_processes).imap_unordered(process_input_file, input_files)
#     for result, input_file in results:
#         print(f"#  Done: {input_file}")
# 
# print("#")
# print("##################################################")
# print("#")
# print("# BATCH-ELEMENT-level processing done.")
# print("#")
# print("##################################################")
# print("#")
# 
# if processed_count == 0:
#     print("##################################################")
#     print("#")
#     print("# -> No files have been processed so far!")
#     print("#")
#     print("# Starting processing on BATCH-LEVEL ...")
#     print("#")
#     print("##################################################")
#     print("#")
# 
#     batch_input_dir = join('/', workflow_dir, operator_in_dir)
#     batch_output_dir = join('/', workflow_dir, operator_in_dir)
# 
#     # check if input dir present
#     if not exists(batch_input_dir):
#         print("#")
#         print(f"# Input-dir: {batch_input_dir} does not exists!")
#         print("# -> skipping")
#         print("#")
#     else:
#         # creating output dir
#         Path(batch_output_dir).mkdir(parents=True, exist_ok=True)
# 
#         # creating output dir
#         input_files = glob(join(batch_input_dir, input_file_extension), recursive=True)
#         print(f"# Found {len(input_files)} input-files!")
# 
#         # Single process:
#         # Loop for every input-file found with extension 'input_file_extension'
#         for input_file in input_files:
#             result, input_file = process_input_file(filepath=input_file)
#         
#         # Alternative with multi-processing
#         results = ThreadPool(parallel_processes).imap_unordered(process_input_file, input_files)
#         for result, input_file in results:
#             print(f"#  Done: {input_file}")
# 
#     print("#")
#     print("##################################################")
#     print("#")
#     print("# BATCH-LEVEL-level processing done.")
#     print("#")
#     print("##################################################")
#     print("#")
# 
# if processed_count == 0:
#     print("#")
#     print("##################################################")
#     print("#")
#     print("##################  ERROR  #######################")
#     print("#")
#     print("# ----> NO FILES HAVE BEEN PROCESSED!")
#     print("#")
#     print("##################################################")
#     print("#")
#     exit(1)
# else:
#     print("#")
#     print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
#     print("#")
#     print("# DONE #")

    