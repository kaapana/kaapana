#/bin/bash
for dir in /$WORKFLOW_DIR/$BATCH_NAME/*       # list directories in the form "/tmp/dirname/"
do
        INPUTDIRFIXED="$dir/$OPERATOR_IN_DIR_FIXED"
        INPUTDIRMOVING="$dir/$OPERATOR_IN_DIR_MOVING"
        OUTPUTDIR="$dir/$OPERATOR_OUT_DIR"
        echo ${INPUTDIRFIXED}
        echo ${INPUTDIRMOVING}
        echo ${OUTPUTDIR}
        mkdir -p $OUTPUTDIR
        # elastix
        # -f        fixed image
        # -m        moving image
        # -out      output directory
        # -p        parameter file, elastix handles 1 or more "-p"

        FIXED_IMAGE=$(find $INPUTDIRFIXED \( -name "*.nrrd" -o -name "*.nii" -o -name "*.dcm" \) | head -n 1)
        MOVING_IMAGE=$(find $INPUTDIRMOVING \( -name "*.nrrd" -o -name "*.nii" -o -name "*.dcm" \) | head -n 1)



        elastix -f $FIXED_IMAGE \
                -m $MOVING_IMAGE \
                -out $OUTPUTDIR \
                -p /kaapana/app/rigid-registration.txt \
                -p /kaapana/app/defo-registration.txt
done


