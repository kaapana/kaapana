#! /bin/bash
set -eu -o pipefail

ROOT_FIXED_DIR="/home/kaapana/fixed"
ROOT_MOVING_DIR="/home/kaapana/moving"
ROOT_OUTPUT_DIR="/home/kaapana/registered"

FIXED_IMAGE=$( find ${ROOT_FIXED_DIR} -maxdepth 2 -mindepth 2 -type f -name *.nrrd)
MOVING_IMAGES=$( find ${ROOT_MOVING_DIR} -maxdepth 2 -mindepth 2 -type f -name *.nrrd)

echo "Start registering images"

mkdir -p /tmp

for MOVING_IMAGE in ${MOVING_IMAGES}; do
    IDENTIFIER=$( basename ${MOVING_IMAGE} )
    echo "Register ${MOVING_IMAGE} to target ${FIXED_IMAGE}"
    mkdir -p ${ROOT_OUTPUT_DIR}/${IDENTIFIER}
    /kaapana/app/apps/MitkMatchImage.sh \
        -t ${FIXED_IMAGE}\
        -m ${MOVING_IMAGE}\
        -o /tmp/${IDENTIFIER}_registration_object.mapr\
        -a /kaapana/app/bin/mdra-0-14_MITK_MultiModal_rigid_default.so

    /kaapana/app/apps/MitkMapImage.sh \
        -t ${FIXED_IMAGE}\
        -i ${MOVING_IMAGE}\
        -r /tmp/${IDENTIFIER}_registration_object.mapr\
        -o ${ROOT_OUTPUT_DIR}/${IDENTIFIER}/${IDENTIFIER}
done