import os
import glob
import time
from typing import List
import warnings
from subprocess import PIPE, run
import pydicom
import requests
from pathlib import Path

HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
HTTP_PORT = os.getenv("HTTP_PORT", "8080")
### If the environment variable AETITLE is "NONE", then I want to set AETITLE = None
AETITLE = os.getenv("AETITLE", "NONE")
AETITLE = None if AETITLE == "NONE" else AETITLE
LEVEL = os.getenv("LEVEL", "element")

print(f"AETITLE: {AETITLE}")
print(f"LEVEL: {LEVEL}")

dicom_sent_count = 0


def send_dicom_data(send_dir, aetitle=AETITLE, timeout=60):
    global dicom_sent_count

    dicom_list: List[Path] = sorted(
        [
            f
            for f in Path(send_dir).rglob("*")
            if f.is_file() and pydicom.misc.is_dicom(f)
        ]
    )

    if len(dicom_list) == 0:
        print(send_dir)
        print("############### No dicoms found...! Skipping to next Batch.")
        # raise FileNotFoundError # Not very elegant, but it still fails if nothing is processed. Maybe would be better if the dag would specify an "allow partial fail" parameter.
        return

    for dicom_dir, _, _ in os.walk(send_dir):
        dicom_list = [
            f
            for f in Path(dicom_dir).glob("*")
            if f.is_file() and pydicom.misc.is_dicom(f)
        ]

        if len(dicom_list) == 0:
            continue

        dcm_file = pydicom.dcmread(dicom_list[0])
        series_uid = str(dcm_file[0x0020, 0x000E].value)

        print(
            f"Found {len(dicom_list)} file(s) in {dicom_dir}. Will use series_uuid {series_uid}"
        )
        if aetitle is None:
            if "WORKFLOW_NAME" in os.environ:
                aetitle = os.environ["WORKFLOW_NAME"]
                print(f"Using workflow_name as aetitle:    {aetitle}")
            else:
                try:
                    aetitle = str(dcm_file[0x012, 0x020].value)
                    print(f"Found aetitle    {aetitle}")
                except Exception as e:
                    print(f"Could not load aetitle: {e}")
                    aetitle = "KAAPANA export"
                    print(f"Using default aetitle {aetitle}")

        print(f"Sending {dicom_dir} to {HOST} {PORT} with aetitle {aetitle}")
        # To process even if the input contains non-DICOM files the --no-halt option is needed (e.g. zip-upload functionality)
        env = dict(os.environ)
        command = [
            "dcmsend",
            "-v",
            f"{HOST}",
            f"{PORT}",
            "-aet",
            "kaapana",
            "-aec",
            f"{aetitle}",
            "--scan-directories",
            "--no-halt",
            f"{dicom_dir}",
        ]
        print(" ".join(command))
        max_retries = 5
        try_count = 0
        while try_count < max_retries:
            print("Try: {}".format(try_count))
            try_count += 1
            try:
                output = run(
                    command,
                    stdout=PIPE,
                    stderr=PIPE,
                    universal_newlines=True,
                    env=env,
                    timeout=timeout,
                )
                if output.returncode != 0 or "with status SUCCESS" not in str(output):
                    print("############### Something went wrong with dcmsend!")
                    for line in str(output).split("\\n"):
                        print(line)
                    print("##################################################")
                    # exit(1)
                else:
                    print(f"Success! output: {output}")
                    print("")
                    break
            except Exception as e:
                print(f"Something went wrong: {e}, trying again!")

        if try_count >= max_retries:
            print("------------------------------------")
            print("Max retries reached!")
            print("------------------------------------")
            raise ValueError(f"Something went wrong with dcmsend!")

        dicom_sent_count += 1


if LEVEL == "element":
    batch_folders = sorted(
        [
            f
            for f in glob.glob(
                os.path.join(
                    "/", os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"], "*"
                )
            )
            if os.path.isdir(f)
        ]
    )

    for batch_element_dir in batch_folders:
        element_input_dir = os.path.join(
            batch_element_dir, os.environ["OPERATOR_IN_DIR"]
        )
        send_dicom_data(element_input_dir, timeout=600)

elif LEVEL == "batch":
    batch_input_dir = os.path.join(
        "/", os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_IN_DIR"]
    )
    print(f"Sending DICOM data from batch-level: {batch_input_dir}")
    send_dicom_data(batch_input_dir, timeout=3600)
else:
    raise NameError(
        'level must be either "element" or "batch". \
        If batch, an operator folder next to the batch folder with .dcm files is expected. \
        If element, *.dcm are expected in the corresponding operator with .dcm files is expected.'
    )

if dicom_sent_count == 0:
    print("##################################################")
    print("#")
    print("############### Something went wrong!")
    print("# --> no DICOM sent !")
    print("# ABORT")
    print("#")
    print("##################################################")
    exit(1)
