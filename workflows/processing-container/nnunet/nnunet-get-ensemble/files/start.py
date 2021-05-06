import sys
import os
import urllib.request
import zipfile
import time
from glob import glob
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from os.path import join, basename, normpath

processed_count = 0
workflow_dir = os.getenv('WORKFLOW_DIR', "data")
output_dir = os.getenv('OPERATOR_OUT_DIR', "/models")

def delete_file(target_file):
    try:
        os.remove(target_file)
    except Exception as e:
        print(e)
        pass

print("------------------------------------")
print(f"--  Starting extract ensemble ")
print("------------------------------------")
print("#")
ensemble_zip_models = glob("/tmp/ensemble_models/*.zip", recursive=True)
if len(ensemble_zip_models) == 0:
    print("# No zip-file models could be found!")
    exit(1)

batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]
for batch_element_dir in batch_folders:
    zip_dir_path = join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    zip_files = glob(join(zip_dir_path, "*.zip"), recursive=True)

    if len(zip_files) == 0:
        print("# No zip-files could be found on batch-element-level")
        break
    elif len(zip_files) != 1:
        print("# More than one zip-files were found -> unexpected -> abort.")
        exit(1)

    try:
        target_file = zip_files[0]

        if target_level == "default":
            models_dir = "/models/nnUNet"
        elif target_level == "batch":
            models_dir = os.path.join(workflow_dir, output_dir)
        elif target_level == "batch_element":
            models_dir = os.path.join(batch_element_dir, output_dir)
        else:
            print(f"#")
            print(f"# ERROR")
            print(f"#")
            print(f"# target_level: {target_level} not supported!")
            print(f"#")
            exit(1)

        Path(models_dir).mkdir(parents=True, exist_ok=True)

        print(f"# Unzipping {target_file} -> {models_dir}")
        with zipfile.ZipFile(target_file, "r") as zip_ref:
            zip_ref.extractall(models_dir)
            processed_count += 1
    except Exception as e:
        print("Could not extract model: {}".format(target_file))
        print("Target dir: {}".format(models_dir))
        print("Abort.")
        print('MSG: ' + str(e))
        exit(1)

if processed_count == 0:
    print("# Searching for zip-files on batch-level...")
    batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
    zip_files = glob.glob(os.path.join(batch_input_dir, "*.zip"), recursive=True)

    if len(zip_files) == 0:
        print("# No zip-files could be found on batch-level")
        exit(1)
    elif len(zip_files) != 1:
        print("# More than one zip-files were found -> unexpected -> abort.")
        exit(1)

    try:
        target_file = zip_files[0]
        with zipfile.ZipFile(target_file, "r") as zip_ref:
            zip_ref.extractall(models_dir)
            processed_count += 1
    except Exception as e:
        print("Could not extract model: {}".format(target_file))
        print("Target dir: {}".format(models_dir))
        print("Abort.")
        print('MSG: ' + str(e))
        exit(1)

print("# ✓ successfully extracted model into model-dir.")
print("# DONE")
exit(0)


print("DONE")
exit(0)
