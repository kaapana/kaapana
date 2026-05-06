#! /bin/bash
set -eu -o pipefail

ROOT_INPUT_NRRD_DIR="/kaapana/app/nrrd"
ROOT_REFERENCE_DIR="/kaapana/app/reference"
ROOT_OUTPUT_NRRD_DIR="/kaapana/app/dicom"

echo "Start conversion"

for INPUT_NRRD_FILE in $( find ${ROOT_INPUT_NRRD_DIR} -mindepth 2 -maxdepth 2 -type f -name *.nrrd ); do
    IDENTIFIER=$( basename $( dirname ${INPUT_NRRD_FILE} ))
    mkdir -p ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}

    echo "Convert ${INPUT_NRRD_FILE}"

    python3 -u /kaapana/app/nrrd_to_dicom.py\
        -i ${INPUT_NRRD_FILE}\
        -r ${ROOT_REFERENCE_DIR}/${IDENTIFIER}\
        -o ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}/
done