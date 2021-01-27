import sys
import os
import glob
import pydicom
from subprocess import PIPE, run
from pathlib import Path

converter_count = 0


def generate_dicom(pdf_path, output_dir, title="PDF", timeout=20):
    global converter_count

    dcm_pdf_path = os.path.join(output_dir, os.path.basename(pdf_path).replace('pdf','dcm'))
    Path(os.path.dirname(dcm_pdf_path)).mkdir(parents=True, exist_ok=True)

    study_uid = os.getenv("STUDY_UID", "NONE")
    study_uid = study_uid if study_uid != "NONE" else None

    aetitle = os.getenv("AETITLE", "NONE")
    aetitle = aetitle if aetitle != "NONE" else None

    dicom_input_dir = os.getenv("DICOM_IN_DIR", "NONE")
    dicom_input_dir = None if dicom_input_dir == "NONE" else os.path.join(batch_element_dir, dicom_input_dir)

    if dicom_input_dir is None:
        print("############### No DICOM specified -> generate study and series IDs...")
        command = [
            "pdf2dcm",
            "--key", "0012,0020={}".format(aetitle),
            "--key", "0020,000D={}".format(study_uid),
            "--generate",
            "--title", "{}".format(title),
        ]
    else:
        input_dcm_files = sorted(glob.glob(os.path.join(dicom_input_dir, "*.dcm*"), recursive=True))
        if len(input_dcm_files) == 0:
            print("No DICOM found at: {}".format(dicom_input_dir))
            print("abort.")
            exit(1)

        try:
            print("Reading DICOM metadata: {}".format(input_dcm_files[0]))
            dicom_file = pydicom.dcmread(input_dcm_files[0])
            study_uid = dicom_file[0x0020, 0x000D].value
            print("-> 'study_uid' ok")
            series_uid = dicom_file[0x0020, 0x000E].value
            print("-> 'series_uid' ok: {}".format(series_uid))
            modality = dicom_file[0x0008, 0x0060].value
            print("-> 'modality' ok: {}".format(modality))
            aetitle = dicom_file[0x012, 0x020].value
            print("-> 'aetitle' ok: {}".format(aetitle))
        except Exception as e:
            print("Error while reading DICOM metadata!")
            print(e)
            print("abort.")
            exit(1)

        command = [
            "pdf2dcm",
            "--key", "0012,0020={}".format(aetitle),
            "--title", "{}".format(title),
            "--study-from", "{}".format(input_dcm_files[0]),
        ]

    command.append(f"{pdf_path}")
    command.append(f"{dcm_pdf_path}")

    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)
    if output.returncode != 0:
        print("############### Something went wrong with pdf2dcm!")
        for line in str(output).split("\\n"):
            print(line)

        print("##################################################")
        exit(1)
    
    converter_count += 1


# START
pdf_title = os.getenv("PDF_TITLE", "PDF")

batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]
for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_IN_DIR", ""))
    element_output_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_OUT_DIR", ""))

    pdf_list = glob.glob(os.path.join(element_input_dir, "*.pdf"))
    if len(pdf_list) == 0:
        print("############### no *.pdf file found at {} ".format(element_input_dir))
        continue

    for pdf in pdf_list:
        if not os.path.exists(element_output_dir):
            os.makedirs(element_output_dir)
        print("##################################################")
        print("#")
        print("# Found file: {}".format(pdf))
        print("#")
        generate_dicom(pdf_path=pdf, output_dir=element_output_dir, title=pdf_title)


print("##################################################")
print("#")
print("# Searching for files on batch-level....")
print("#")
print("##################################################")
print("#")

batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
batch_output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])

print(f"# batch_input_dir:  {batch_input_dir}")
print(f"# batch_output_dir: {batch_output_dir}")

pdf_list = glob.glob(os.path.join(batch_input_dir, "*.pdf"))
if len(pdf_list) == 0:
    print("############### no *.pdf file found at {} ".format(batch_input_dir))

for pdf in pdf_list:
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)
    print("##################################################")
    print("#")
    print("# Found file: {}".format(pdf))
    print("#")
    generate_dicom(pdf_path=pdf, output_dir=batch_output_dir, title=pdf_title)


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


# DCMTK DOCS:
#
# document title:

#   +t   --title  [t]itle: string (default: empty)
#          document title

#   +cn  --concept-name  [CSD] [CV] [CM]: string (default: empty)
#          coded representation of document title defined by coding
#          scheme designator CSD, code value CV and code meaning CM

# patient data:

#   +pn  --patient-name  [n]ame: string
#          patient's name in DICOM PN syntax

#   +pi  --patient-id  [i]d: string
#          patient identifier

#   +pb  --patient-birthdate  [d]ate: string (YYYYMMDD)
#          patient's birth date

#   +ps  --patient-sex  [s]ex: string (M, F or O)
#          patient's sex

# study and series:

#   +sg  --generate
#          generate new study and series UIDs (default)

#   +st  --study-from  [f]ilename: string
#          read patient/study data from DICOM file

#   +se  --series-from  [f]ilename: string
#          read patient/study/series data from DICOM file

# instance number:

#   +i1  --instance-one
#          use instance number 1 (default, not with +se)

#   +ii  --instance-inc
#          increment instance number (only with +se)

#   +is  --instance-set [i]nstance number: integer
#          use instance number i

# burned-in annotation:

#   +an  --annotation-yes
#          document contains patient identifying data (default)

#   -an  --annotation-no
#          document does not contain patient identifying data
