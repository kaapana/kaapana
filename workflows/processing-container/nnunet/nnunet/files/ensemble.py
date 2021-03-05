from nnunet.inference.ensemble_predictions import merge
from pathlib import Path
import os
from os import getenv
from os.path import join, exists
from glob import glob

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None

threads_nifiti = getenv("INF_THREADS_NIFTI", "None")
threads_nifiti = int(threads_nifiti) if threads_nifiti.lower() != "none" else 2

override = True
store_npz = True
postprocessing_file = None

print("##################################################")
print("#")
print("# Starting nnUNet simple predict....")
print("#")
print(f"# override:            {override}")
print(f"# threads_nifiti:      {threads_nifiti}")
print(f"# operator_in_dir:     {operator_in_dir}")
print(f"# operator_out_dir:    {operator_out_dir}")
print(f"# postprocessing_file: {postprocessing_file}")
print("#")
print("##################################################")
print("#")

processed_count = 0
ensemble_dirs = []

output_dir = os.path.join('/', workflow_dir, operator_out_dir)

batch_folders = [f for f in glob(join('/', workflow_dir, batch_name, '*'))]
for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, operator_in_dir)
    if exists(element_input_dir):
        print(f"# Adding {element_input_dir} to the ensemble...")
        ensemble_dirs.append(element_input_dir)
    else:
        print(f"# Input-Dir {element_input_dir} not found! -> unexpected -> ABORT")
        print(f"#")
        exit(1)

if len(ensemble_dirs) == 0:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> NO INPUT-DIRS HAVE BEEN FOUND!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)

print(f"#")
print(f"# Evaluating the ensemble....")
print(f"# output_dir:    {output_dir}")
print(f"# ensemble_dirs: {ensemble_dirs}")
print(f"#")

Path(output_dir).mkdir(parents=True, exist_ok=True)

merge(
    folders=ensemble_dirs,
    output_folder=output_dir,
    threads=threads_nifiti,
    postprocessing_file=postprocessing_file,
    store_npz=store_npz,
    override=override,
)

print("# DONE #")
