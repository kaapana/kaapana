import os
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path

import torch
import monai
from monai.bundle import ConfigParser
from monai.data import decollate_batch

# For multiprocessing -> usually you should scale via multiple containers!
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run
execution_timeout=10
 
# Counter to check if smth has been processed
processed_count = 0

# MONAI inference process
def process_input_file(filepath): 
    global processed_count

    # point dataloader to dataset
    # data_in_dir = os.path.join("/data/")
    datalist = [filepath]
    model_config["datalist"] = datalist
    dataloader = model_config.get_parsed_content("dataloader")

    model.load_state_dict(torch.load(checkpoint, map_location=device))
    model.eval()
    results = []
    with torch.no_grad():
        for d in dataloader:
            images = d["image"].to(device)
            d["pred"] = inferer(images, network=model)
            results.append([postprocessing(i) for i in decollate_batch(d)]) # fails --> remove Invertd post-processing transform in inference.json

    processed_count += 1
    return True, filepath


# workflow_dir = getenv("WORKFLOW_DIR", "None")
# workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
# assert workflow_dir is not None
workflow_dir = "data"

# batch_name = getenv("BATCH_NAME", "None")
# batch_name = batch_name if batch_name.lower() != "none" else None
# assert batch_name is not None
batch_name = "batch"

# operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
# operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
# assert operator_in_dir is not None
operator_in_dir = "dcm-converter"

# operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
# operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
# assert operator_out_dir is not None
operator_out_dir = "monai-inference"

boolean_var = getenv("SOME_BOOLEAN_VAR", "False")
boolean_var = True if boolean_var.lower() == "true" else False

# File-extension to search for in the input-dir
input_file_extension = "*.nii.gz"

# How many processes should be started?
parallel_processes = 3

### MONAI inference specific global vars
# model_dir
monai_task_n_version = "spleen_ct_segmentation_v0.3.7"    # TODO: get as input
monai_task = "spleen_ct_segmentation"
# model_dir = os.path.join("/models/MONAI", monai_task_n_version)
model_dir = "models/MONAI/spleen_ct_segmentation_v0.3.7"
# GPU device
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
# get loaded MONAI model
model_config_file = os.path.join(model_dir, monai_task, "configs", "inference.json")
model_config = ConfigParser()
model_config.read_config(model_config_file)
# update conf variables in model_config
model_config["bundle_root"] = model_dir
model_config["output_dir"] = operator_out_dir
# get checkpoint of model
checkpoint = os.path.join(model_dir, monai_task, "models", "model.pt")
# get preprocessing, model, inferer, postprocessing
preprocessing = model_config.get_parsed_content("preprocessing")
model = model_config.get_parsed_content("network").to(device)
inferer = model_config.get_parsed_content("inferer")
postprocessing = model_config.get_parsed_content("postprocessing")



print("##################################################")
print("#")
print(f"# Starting operator {operator_out_dir}:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print(f"# boolean_var:      {boolean_var}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

# Loop for every batch-element (usually series)
# batch_folders = sorted([f for f in glob(join('/', workflow_dir, batch_name, '*'))]) # /home/m391k/kaapana/data
batch_folders = sorted([f for f in glob(join('/home/m391k/kaapana/data', batch_name, '*'))])
for batch_element_dir in batch_folders:
    print("#")
    print(f"# Processing batch-element {batch_element_dir}")
    print("#")
    element_input_dir = join(batch_element_dir, operator_in_dir)
    element_output_dir = join(batch_element_dir, operator_out_dir)

    # check if input dir present
    if not exists(element_input_dir):
        print("#")
        print(f"# Input-dir: {element_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
        continue

    # creating output dir
    Path(element_output_dir).mkdir(parents=True, exist_ok=True)

    # creating output dir
    input_files = glob(join(element_input_dir, input_file_extension), recursive=True)
    print(f"# Found {len(input_files)} input-files!")

    # Single process:
    # Loop for every input-file found with extension 'input_file_extension'
    for input_file in input_files:
        result, input_file = process_input_file(filepath=input_file)
    
    # Alternative with multi-processing
    results = ThreadPool(parallel_processes).imap_unordered(process_input_file, input_files)
    for result, input_file in results:
        print(f"#  Done: {input_file}")

print("#")
print("##################################################")
print("#")
print("# BATCH-ELEMENT-level processing done.")
print("#")
print("##################################################")
print("#")

if processed_count == 0:
    print("##################################################")
    print("#")
    print("# -> No files have been processed so far!")
    print("#")
    print("# Starting processing on BATCH-LEVEL ...")
    print("#")
    print("##################################################")
    print("#")

    batch_input_dir = join('/', workflow_dir, operator_in_dir)
    batch_output_dir = join('/', workflow_dir, operator_in_dir)

    # check if input dir present
    if not exists(batch_input_dir):
        print("#")
        print(f"# Input-dir: {batch_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
    else:
        # creating output dir
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        # creating output dir
        input_files = glob(join(batch_input_dir, input_file_extension), recursive=True)
        print(f"# Found {len(input_files)} input-files!")

        # Single process:
        # Loop for every input-file found with extension 'input_file_extension'
        for input_file in input_files:
            result, input_file = process_input_file(filepath=input_file)
        
        # Alternative with multi-processing
        results = ThreadPool(parallel_processes).imap_unordered(process_input_file, input_files)
        for result, input_file in results:
            print(f"#  Done: {input_file}")

    print("#")
    print("##################################################")
    print("#")
    print("# BATCH-LEVEL-level processing done.")
    print("#")
    print("##################################################")
    print("#")

if processed_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("##################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)
else:
    print("#")
    print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
    print("#")
    print("# DONE #")

    