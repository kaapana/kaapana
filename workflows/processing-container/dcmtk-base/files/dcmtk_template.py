import sys
import os
import glob
from subprocess import PIPE, run
from pathlib import Path

converter_count = 0


def process_file(input_file, output_dir, input_dir=None, timeout=20):
    global converter_count, aetitle, study_uid, study_description, patient_id, patient_name

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    custom_info = os.getenv("INFO", "None")
    custom_info = None if custom_info == "None" else custom_info

    output_file = os.path.join(output_dir, os.path.basename(input_file).replace('REPLACE', 'REPLACE'))

    additional_keys = []

    if aetitle != None:
        additional_keys.append(f"0012,0020={aetitle}")
    if study_uid != None:
        additional_keys.append(f"0020,000D={study_uid}")
    if study_description != None:
        additional_keys.append(f"0008,1030={study_description}")
    if patient_id != None:
        additional_keys.append(f"0010,0020={patient_id}")
    if patient_name != None:
        additional_keys.append(f"0010,0010={patient_name}")

    command = [
        "<dcmtk-command>",
        "--generate",
        "--title", f"{title}",
    ]

    for add_key in additional_keys:
        command.append("--key")
        command.append(add_key)

    command.append(f"{input_file}")
    command.append(f"{output_file}")

    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)
    if output.returncode != 0:
        print("##################################################")
        print("#")
        print("##### COMMAND FAILED!")
        for line in str(output).split("\\n"):
            print(line)

        print("#")
        print("##################################################")
        exit(1)

    print("# File processed.")
    converter_count += 1


# START
aetitle = os.getenv("AETITLE", "None")
aetitle = None if aetitle == "None" else aetitle

study_uid = os.getenv("STUDY_UID", "None")
study_uid = None if study_uid == "None" else study_uid

study_description = os.getenv("STUDY_DES", "None")
study_description = None if study_description == "None" else study_description

patient_id = os.getenv("PAT_ID", "None")
patient_id = None if patient_id == "None" else patient_id

patient_name = os.getenv("PAT_NAME", "None")
patient_name = None if patient_name == "None" else patient_name

file_extensions = ["*.pdf", "*.txt"]


print("##################################################")
print("#")
print("# Searching for files on element level....")
print("#")
print(f"# extensions: {file_extensions}")
print("#")
print("##################################################")
print("#")
batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]
for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_IN_DIR", ""))
    element_output_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_OUT_DIR", ""))

    files_grabbed = []
    for extension in file_extensions:
        files_grabbed.extend(glob.glob(os.path.join(element_input_dir, extension), recursive=True))

    if len(files_grabbed) == 0:
        print(f"############### No {extensions} files found at {element_input_dir} -> continue ")
        continue

    for file_found in files_grabbed:
        print("##################################################")
        print("#")
        print("# Processing file: {}".format(file_found))
        print("#")
        process_file(input_file=file_found, output_dir=element_output_dir, input_dir=element_input_dir)


print("##################################################")
print("#")
print("# Searching for files on batch-level....")
print("#")
print(f"# extensions: {file_extensions}")
print("#")
print("##################################################")
print("#")

batch_input_dir=os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
batch_output_dir=os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])

files_grabbed=[]
for extension in file_extensions:
    files_grabbed.extend(glob.glob(os.path.join(batch_input_dir, extension), recursive=True)

if len(files_grabbed) == 0:
    print(f"############### No {extensions} files found at {batch_input_dir} -> continue ")

else:
    for file_found in files_grabbed:
        print("##################################################")
        print("#")
        print("# Processing file: {}".format(file_found))
        print("#")
        process_file(input_file=file_found, output_dir=batch_output_dir, input_dir=batch_input_dir)


if converter_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN CONVERTED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)

print("#")
print("#")
print("##################################################")
print("#")
print("##################  DONE  ########################")
print("#")
print("##################################################")
print("#")
print("#")
