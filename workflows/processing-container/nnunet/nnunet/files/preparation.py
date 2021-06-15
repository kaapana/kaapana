import os
import json
import glob
import pydicom
import shutil
import pathlib


if __name__ == "__main__":
    print("# Starting nnUNet data preparation...")

    task = os.getenv("TASK", None)
    input_dirs = os.getenv("INPUT_MODALITY_DIRS", "").split(",")
    operator_output_dir = os.getenv("OPERATOR_OUT_DIR", None)

    if operator_output_dir == None:
        print("# ENV 'OPERATOR_OUT_DIR' not set!")
        exit(1)

    if task == None:
        print("# Env 'TASK' has to be specified!")
        print("# Abort!")
        exit(1)

    task_body_part = os.getenv("BODY_PART", "N/A")
    task_modalities = os.getenv("INPUT", "ENV NOT FOUND!").split(",")
    task_protocols = os.getenv("PROTOCOLS", "ENV NOT FOUND!").split(",")
    task_organs = os.getenv("TARGETS", "ENV NOT FOUND!").split(",")

    print("#")
    print("# Configuration found: ")
    print("#")
    print(f"# task_organs:     {task_organs}")
    print(f"# task_body_part:  {task_body_part}")
    print(f"# task_protocols:  {task_protocols}")
    print(f"# task_modalities: {task_modalities}")
    print("#")

    batches_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'])
    batch_folders = sorted([f for f in glob.glob(os.path.join(batches_dir, '*'))])
    print("# batches_dir {}".format(batches_dir))
    print("# Found {} batches".format(len(batch_folders)))

    output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], operator_output_dir)
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    for batch_element_dir in batch_folders:
        if len(input_dirs) != len(task_protocols):
            print("# Wrong input-protocol-count!")
            print("# Count input operators: {}".format(len(input_dirs)))
            print("# Count task-protocols needed: {}".format(len(task_protocols)))
            print("# Needed protocols: {}".format(task_protocols))
            print("# Abort!")
            exit(1)

        protocol_index = 0
        for input_nfiti in input_dirs:
            nifti_dir = os.path.join(batch_element_dir, input_nfiti)
            nifti_files = sorted(glob.glob(os.path.join(nifti_dir, "*.nii*"), recursive=True))
            nifti_count = len(nifti_files)

            print("# NIFTI_DIR: {}".format(nifti_dir))
            print("# NIFTI_COUNT: {}".format(nifti_count))

            if nifti_count == 0:
                print("# #")
                print("# #")
                print("# # No NIFTI found!")
                print("# # Abort!")
                print("# #")
                print("# #")
                exit(1)

            for nifti_file in nifti_files:
                file_name = os.path.basename(nifti_file).split(".nii.gz")[0]
                target_path = os.path.join(output_dir, "{}_{:04d}.nii.gz".format(file_name, protocol_index))
                print("# Copy NIFTI: {} -> {}".format(nifti_file, target_path))
                shutil.copyfile(nifti_file, target_path)
                protocol_index += 1
