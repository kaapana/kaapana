#! /bin/bash
set -eu -o pipefail

ROOT_INPUT_NRRD_DIR="/home/kaapana/nrrd"
ROOT_REFERENCE_DIR="/home/kaapana/reference"
ROOT_OUTPUT_NRRD_DIR="/home/kaapana/dicom"

echo "Start conversion"

for INPUT_NRRD_FILE in $( find ${ROOT_INPUT_NRRD_DIR} -mindepth 2 -maxdepth 2 -type f -name *.nrrd ); do
    IDENTIFIER=$( basename $( dirname ${INPUT_NRRD_FILE} ))
    mkdir -p ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}

    echo "Convert ${INPUT_NRRD_FILE}"

    python3 -u /home/kaapana/nrrd_to_dicom.py\
        -i ${INPUT_NRRD_FILE}\
        -r ${ROOT_REFERENCE_DIR}/${IDENTIFIER}\
        -o ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}/
done