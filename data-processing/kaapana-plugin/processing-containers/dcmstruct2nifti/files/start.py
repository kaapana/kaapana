import os
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
import json
import shutil
from dcmrtstruct2nii import dcmrtstruct2nii, list_rt_structs

# For multiprocessing -> usually you should scale via multiple containers!
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run
execution_timeout = 10

# Counter to check if smth has been processed
processed_count = 0


def generate_meta_info(result_dir):
    result_niftis = glob(join(result_dir, "*.nii.gz"), recursive=False)

    seg_count = 0
    for result in result_niftis:
        seg_count += 1
        if "image.nii.gz" in result:
            continue
        target_dir = dirname(dirname(result))
        extracted_label = basename(result).replace("mask_","").replace(".nii.gz","")
        print("#")
        if seg_filter is not None and extracted_label.lower().replace(',',' ').replace(' ','') not in seg_filter:
            print(f"# extracted_label {extracted_label.lower().replace(',',' ').replace(' ','')} not in filters {seg_filter} -> ignoring")
            continue
        print("#")
        file_id = f"{basename(result).split('_')[0]}_{seg_count}"
        label_id = 255
        label_string = f"--{label_id}--{extracted_label}.nii.gz"    
        new_filename = join(target_dir,f"{file_id}{label_string}")
        print("#")
        print("#")
        print(f"# result:          {result}")
        print(f"# file_id:         {file_id}")
        print(f"# target_dir:      {target_dir}")
        print(f"# extracted_label: {extracted_label}")
        print(f"# label_string:    {label_string}")
        print(f"# new_filename:    {new_filename}")
        print("#")

        shutil.move(result,new_filename)

        meta_temlate = {
            "segmentAttributes": [
            [{
                "SegmentLabel": extracted_label.replace('-',' '),
                "labelID": label_id,
            }]

            ]
        }
        
        meta_path=join(dirname(new_filename),f"{file_id}-meta.json")
        with open(meta_path, "w", encoding='utf-8') as jsonData:
            json.dump(meta_temlate, jsonData, indent=4, sort_keys=True, ensure_ascii=True)
    
    shutil.rmtree(result_dir)


def process_input_file(struct_path, dicom_dir, output_path):
    global processed_count

    dcmrtstruct2nii(struct_path, dicom_dir, output_path)
    processed_count += 1
    return True, struct_path


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

seg_filter = os.environ.get('SEG_FILTER', "")
if seg_filter != "":
    seg_filter = seg_filter.lower().replace(" ","").split(",")
    print(f"Set filters: {seg_filter}")
else:
    seg_filter = None

dicom_in_dir = getenv("DICOM_IN_DIR", "None")
dicom_in_dir = dicom_in_dir if dicom_in_dir.lower() != "none" else None
assert dicom_in_dir is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

boolean_var = getenv("SOME_BOOLEAN_VAR", "False")
boolean_var = True if boolean_var.lower() == "true" else False

# File-extension to search for in the input-dir
input_file_extension = "*.dcm"

# How many processes should be started?
parallel_processes = 3

print("##################################################")
print("#")
print("# Starting operator xyz:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# dicom_in_dir:     {dicom_in_dir}")
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
batch_folders = sorted([f for f in glob(join('/', workflow_dir, batch_name, '*'))])
for batch_element_dir in batch_folders:
    print("#")
    print(f"# Processing batch-element {batch_element_dir}")
    print("#")
    element_dicom_dir = join(batch_element_dir, dicom_in_dir)
    assert exists(element_dicom_dir)
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
        output_path = join(element_output_dir, basename(batch_element_dir))
        result, input_file = process_input_file(
            struct_path=input_file,
            dicom_dir=element_dicom_dir,
            output_path=output_path
        )
    generate_meta_info(result_dir=output_path)


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

    batch_dicom_dir = join(batch_input_dir, dicom_in_dir)
    assert exists(batch_dicom_dir)

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
        input_files = glob(join(batch_input_dir, input_file_extension), recursive=False)
        print(f"# Found {len(input_files)} input-files!")

        # Single process:
        # Loop for every input-file found with extension 'input_file_extension'
        for input_file in input_files:
            output_path = join(batch_output_dir, "dcmrtstruct2nii")
            result, input_file = process_input_file(
                struct_path=input_file,
                dicom_dir=batch_dicom_dir,
                output_path=output_path
            )
        generate_meta_info(result_dir=output_path)

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
