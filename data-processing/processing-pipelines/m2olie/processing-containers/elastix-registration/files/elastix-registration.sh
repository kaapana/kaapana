#/bin/bash

# elastix
# -f        fixed image
# -m        moving image
# -out      output directory
# -p        parameter file, elastix handles 1 or more "-p"

FIXED_IMAGE=`find $OPERATOR_IN_DIR_FIXED \( -name "*.nrrd" -o -name "*.nii" -o -name "*.dcm" \)`
MOVING_IMAGE=`find $OPERATOR_IN_DIR_MOVING \( -name "*.nrrd" -o -name "*.nii" -o -name "*.dcm" \)`

elastix -f $FIXED_IMAGE \
        -m $MOVING_IMAGE \
        -out $OPERATOR_OUT_DIR \
        -p /kaapana/app/rigid-registration.txt \
        -p /kaapana/app/defo-registration.txt