import sys
import os
import glob
import pydicom
from subprocess import PIPE, run
from pathlib import Path

converter_count = 0


def process_file(input_file, output_dir, input_dir=None, timeout=20):
    global converter_count, aetitle, study_uid, study_description, patient_id, patient_name

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    pdf_title = os.getenv("PDF_TITLE", "None")
    pdf_title = None if pdf_title == "None" else pdf_title

    dicom_input_dir = os.getenv("DICOM_IN_DIR", "None")
    dicom_input_dir = None if dicom_input_dir == "None" else os.path.join(os.path.dirname(input_dir), dicom_input_dir)

    output_file = os.path.join(output_dir, os.path.basename(input_file).replace('pdf', 'dcm'))

    if dicom_input_dir is not None:
        input_dcm_files = sorted(glob.glob(os.path.join(dicom_input_dir, "*.dcm*"), recursive=True))
        if len(input_dcm_files) == 0:
            print("No DICOM found at: {}".format(dicom_input_dir))
            print("abort.")
            exit(1)

        try:
            print(f"# Reading DICOM metadata: {input_dcm_files[0]}")
            dicom_file = pydicom.dcmread(input_dcm_files[0])
            
            dcm_aetitle = dicom_file[0x012, 0x020].value
            aetitle = dcm_aetitle if aetitle is None else aetitle 
            
            dcm_study_uid = dicom_file[0x0020, 0x000D].value
            study_uid = dcm_study_uid if study_uid is None else study_uid 

            dcm_study_description = dicom_file[0x0008, 0x1030].value
            study_description = dcm_study_description if study_description is None else study_description
            
            dcm_patient_id = dicom_file[0x0010, 0x0020].value
            patient_id = dcm_patient_id if patient_id is None else patient_id
            
            dcm_patient_name = dicom_file[0x0010, 0x0010].value
            patient_name = dcm_patient_name if patient_name is None else patient_name
            
        except Exception as e:
            print("##################################################")
            print("#")
            print("# Error while reading DICOM metadata!")
            print(e)
            print("abort.")
            print("#")
            print("##################################################")
            exit(1)

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
        "pdf2dcm",
        "--title", f"{pdf_title}"
    ]

    for add_key in additional_keys:
        command.append("--key")
        command.append(add_key)

    if study_uid == None:
        additional_keys.append("--generate")
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

file_extensions = ["*.pdf"]


print("##################################################")
print("#")
print("# Searching for files on element level....")
print("#")
print(f"# extensions: {file_extensions}")
print("#")
print("##################################################")
print("#")
batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])
for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_IN_DIR", ""))
    element_output_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_OUT_DIR", ""))

    files_grabbed = []
    for extension in file_extensions:
        files_grabbed.extend(glob.glob(os.path.join(element_input_dir, extension), recursive=True))

    if len(files_grabbed) == 0:
        print(f"############### No {file_extensions} files found at {element_input_dir} -> continue ")
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
    files_grabbed.extend(glob.glob(os.path.join(batch_input_dir, extension), recursive=True))

if len(files_grabbed) == 0:
    print(f"############### No {file_extensions} files found at {batch_input_dir} -> continue ")

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
