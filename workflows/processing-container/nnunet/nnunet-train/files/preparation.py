import os
import json
import glob
import pydicom
import shutil
import pathlib
from getTaskInfo import get_task_info


def write_organs_json(task_organs, batch_element_dir):
    organs_json = {"seg_info": task_organs}
    organs_json["algorithm"] = os.getenv("TASK", "na").lower()
    output_dir = os.path.join(batch_element_dir, operator_output_dir, 'seg_info.json')

    with open(output_dir, 'w') as outfile:
        json.dump(organs_json, outfile, sort_keys=True, indent=4)


if __name__ == "__main__":
    print("Starting nnUNet data preparation...")

    task = os.getenv("TASK", None)
    input_dirs = os.getenv("INPUT_NIFTI_DIRS", "").split(";")
    operator_output_dir = os.getenv("OPERATOR_OUT_DIR", None)

    if operator_output_dir == None:
        print("ENV 'OPERATOR_OUT_DIR' not set!")
        exit(1)

    if task == None:
        print("Env 'TASK' has to be specified!")
        print("Abort!")
        exit(1)

    task_info = get_task_info(task)
    task_body_part = task_info["body_part"]
    task_modalities = task_info["modalities"].split(";")
    task_protocolls = task_info["protocols"].split(";")
    task_organs = task_info["organs"].split(";")

    batches_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'])
    batch_folders = [f for f in glob.glob(os.path.join(batches_dir, '*'))]
    print("batches_dir {}".format(batches_dir))
    print("Found {} batches".format(len(batch_folders)))

    output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], operator_output_dir)
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    for batch_element_dir in batch_folders:
        write_organs_json(task_organs=task_organs, batch_element_dir=batch_element_dir)
        if len(input_dirs) != len(task_protocolls):
            print("Wrong input-protocol-count!")
            print("Count input operators: {}".format(len(input_dirs)))
            print("Count task-protocols needed: {}".format(len(task_protocolls)))
            print("Needed protocols: {}".format(task_protocolls))
            print("Abort!")
            exit(1)

        protocol_index = 0
        for input_nfiti in input_dirs:
            nifti_dir = os.path.join(batch_element_dir, input_nfiti)
            nifti_files = sorted(glob.glob(os.path.join(nifti_dir, "*.nii*"), recursive=True))

            print("NIFTI_DIR: {}".format(nifti_dir))
            print("NIFTI_COUNT: {}".format(len(nifti_files)))

            for nifti_file in nifti_files:
                file_name = os.path.basename(nifti_file).split(".nii.gz")[0]
                target_path = os.path.join(output_dir, "{}_{:04d}.nii.gz".format(file_name, protocol_index))
                print("Copy NIFTI: {} -> {}".format(nifti_file, target_path))
                shutil.copyfile(nifti_file, target_path)
                protocol_index += 1
