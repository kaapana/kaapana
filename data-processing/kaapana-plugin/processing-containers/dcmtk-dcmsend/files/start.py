from collections import defaultdict
import glob
import os
from pathlib import Path
from subprocess import PIPE, run
from typing import Dict, List, Optional

import pydicom
from pydicom.dataset import FileDataset
from pydicom.errors import InvalidDicomError
from kaapanapy.helper import load_workflow_config
from kaapanapy.settings import KaapanaSettings

DICOMDIR_SOP_CLASS_UID = "1.2.840.10008.1.3.10"

DEFAULT_SCP = "ANY-SCP"
SERVICES_NAMESPACE = KaapanaSettings().services_namespace
### If the environment variable AETITLE is "NONE", then I want to set AETITLE = None
AETITLE = os.getenv("AETITLE", "NONE")
AETITLE = None if AETITLE == "NONE" else AETITLE
LEVEL = os.getenv("LEVEL", "element")
WORKFLOW_CONFIG = load_workflow_config()
# add TASK_NUM to AETITLE if it exists
TASK_NUM = WORKFLOW_CONFIG.get("workflow_form").get("task_num")
if AETITLE is not None and TASK_NUM is not None:
    AETITLE = AETITLE + str(TASK_NUM)
PROJECT = WORKFLOW_CONFIG.get("project_form")
PROJECT_NAME = PROJECT.get("name")

# if PACS_HOST is "", it will send to the platform itself
PACS_HOST = os.getenv("PACS_HOST") or f"ctp-dicom-service.{SERVICES_NAMESPACE}.svc"
PACS_PORT = os.getenv("PACS_PORT", "11112")
CALLED_AE_TITLE_SCP = os.getenv("CALLED_AE_TITLE_SCP", DEFAULT_SCP)

print(f"AETITLE: {AETITLE}")
print(f"PACS_HOST: {PACS_HOST}")
print(f"PACS_PORT: {PACS_PORT}")
print(f"CALLED_AE_TITLE_SCP: {CALLED_AE_TITLE_SCP}")
print(f"LEVEL: {LEVEL}")

dicom_sent_count = 0


def _load_representative_instance(files: List[Path]) -> Optional[FileDataset]:
    """
    Return the first usable DICOM instance from a list of files.

    Skips:
    - unreadable/corrupt DICOMs
    - DICOMDIR
    - DICOM objects without SeriesInstanceUID
    """
    for f in sorted(files):
        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True)
        except InvalidDicomError:
            print(f"Skipping invalid DICOM: {f}")
            continue
        except Exception as e:
            print(f"Could not read {f}: {e}")
            continue

        if str(ds.get("SOPClassUID", "")) == DICOMDIR_SOP_CLASS_UID:
            print(f"Skipping DICOMDIR: {f}")
            continue

        if not ds.get("SeriesInstanceUID"):
            print(f"Skipping DICOM without SeriesInstanceUID: {f}")
            continue

        return ds

    return None


def send_dicom_data(send_dir, project_name, aetitle=AETITLE, timeout=60):
    global dicom_sent_count

    dicoms_by_dir: Dict[Path, List[Path]] = defaultdict(list)

    # Single traversal over the whole tree
    for f in Path(send_dir).rglob("*"):
        if f.is_file() and pydicom.misc.is_dicom(f):
            dicoms_by_dir[f.parent].append(f)

    if not dicoms_by_dir:
        print(send_dir)
        print("############### No dicoms found...! Skipping to next Batch.")
        return

    for dicom_dir in sorted(dicoms_by_dir):
        dicom_list = sorted(dicoms_by_dir[dicom_dir])

        dcm_file = _load_representative_instance(dicom_list)
        if dcm_file is None:
            print(f"No usable DICOM instance found in {dicom_dir}. Skipping.")
            continue

        series_uid = str(dcm_file.SeriesInstanceUID)

        print(
            f"Found {len(dicom_list)} DICOM file(s) in {dicom_dir}. "
            f"Will use series_uid {series_uid}"
        )

        local_aetitle = aetitle
        if local_aetitle is None:
            if "WORKFLOW_NAME" in os.environ:
                local_aetitle = os.environ["WORKFLOW_NAME"]
                print(f"Using workflow_name as aetitle: {local_aetitle}")
            else:
                try:
                    local_aetitle = str(dcm_file[0x0012, 0x0020].value)
                    print(f"Found aetitle {local_aetitle}")
                except Exception as e:
                    print(f"Could not load aetitle: {e}")
                    local_aetitle = "KAAPANA export"
                    print(f"Using default aetitle {local_aetitle}")

        print(f"Sending {dicom_dir} to {PACS_HOST} {PACS_PORT} with aetitle {local_aetitle}")

        aec = CALLED_AE_TITLE_SCP
        if PACS_HOST == f"ctp-dicom-service.{SERVICES_NAMESPACE}.svc":
            dataset = (
                local_aetitle
                if local_aetitle.startswith("kp-")
                else f"kp-{local_aetitle}"
            )
            if CALLED_AE_TITLE_SCP == DEFAULT_SCP:
                aec = project_name
            aec = aec if aec.startswith("kp-") else f"kp-{aec}"
        else:
            dataset = local_aetitle

        env = dict(os.environ)
        command = [
            "dcmsend",
            "-v",
            f"{PACS_HOST}",
            f"{PACS_PORT}",
            "-aet",
            dataset,
            "-aec",
            aec,
            "--scan-directories",
            "--no-halt",
            str(dicom_dir),
        ]
        print(" ".join(command))

        max_retries = 5
        try_count = 0
        success = False

        while try_count < max_retries:
            print(f"Try: {try_count}")
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

                stdout = output.stdout or ""
                stderr = output.stderr or ""

                if output.returncode == 0:
                    print("Success!")
                    if stdout:
                        print(stdout)
                    if stderr:
                        print(stderr)
                    print("")
                    success = True
                    break

                print("############### Something went wrong with dcmsend!")
                print(f"Return code: {output.returncode}")
                if stdout:
                    print("STDOUT:")
                    print(stdout)
                if stderr:
                    print("STDERR:")
                    print(stderr)
                print("##################################################")

            except Exception as e:
                print(f"Something went wrong: {e}, trying again!")

        if not success:
            print("------------------------------------")
            print("Max retries reached!")
            print("------------------------------------")
            raise ValueError(f"Something went wrong with dcmsend for {dicom_dir}!")

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
        send_dicom_data(element_input_dir, project_name=PROJECT_NAME, timeout=600)

elif LEVEL == "batch":
    batch_input_dir = os.path.join(
        "/", os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_IN_DIR"]
    )
    print(f"Sending DICOM data from batch-level: {batch_input_dir}")
    send_dicom_data(batch_input_dir, project_name=PROJECT_NAME, timeout=3600)
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
