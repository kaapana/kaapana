#bin/bash

function resampling {
    echo "Starting Resampling-Module..."
    Xvfb :99 -screen 0 1024x768x24 &
    export DISPLAY=:99
    exec "$@"

    loop_counter=0
    organ=$(echo "$ORGAN" | awk '{print tolower($0)}')
    echo 'INPUTDIR: '   $INPUTDIR
    echo 'OUTPUTDIR: '  $OUTPUTDIR
    echo 'PARAMETERS: ' $PARAMETERS

    export BULK="False"

    shopt -s nullglob
    for file in $(find $INPUTDIR  -name '*.nrrd'); do
        ((++loop_counter))
        filename=$(basename -- "$file");
        echo "File found: $file"

        IFS=/ read -a path_array <<< $file
        len_array=${#path_array[@]}
        img_dir="${path_array[$len_array-2]}"
        echo "IMG DIR: " $img_dir

        echo "Mkdir $OUTPUTDIR"
        mkdir -p $OUTPUTDIR

        filename="${filename%.*}";
        filename_cut=$(basename $filename .nrrd)  
        echo $filename_cut
        output_filepath=$OUTPUTDIR/$filename_cut'_resample.nrrd';
        echo $output_filepath
            
        echo "###################################################################### CONFIG"
        echo ""
        echo ""
        echo ""
        echo 'output_filepath: ' $output_filepath
        echo "Creating DCM_UID: " $img_dir
        echo "$img_dir" > $OUTPUTDIR/dcm_uid.txt

        dcm_uid=$(cat $OUTPUTDIR/dcm_uid.txt)
        if [ -z "$dcm_uid" ];
        then 
            echo "dcm_uid.txt not found!"
            echo "Path: " $OUTPUTDIR/dcm_uid.txt
            exit 1
        fi

        # install -Dv / $xml_filepath

        echo /src/MitkResampleImage.sh -i $file -o $output_filepath -x 1.3020833730698 -y 1.3020833730698 -z 5.5 $PARAMETERS
        /src/MitkResampleImage.sh -i $file -o $output_filepath -x 1.3020833730698 -y 1.3020833730698 -z 5.5 $PARAMETERS
            # /src/MitkCLGlobalImageFeatures.sh -i $file -o $csv_filepath -x $xml_filepath -m $maskfile -rm 1 -sp 1 -head 1 -fl-head 1 -fo 1 -cooc 1
            
        retVal=$?
        if [ $retVal -ne 0 ]; then
            echo "MitkResample Error!"
            exit 1;
        else
            echo "MitkResample DONE!"
        fi
    done

    if [ "$loop_counter" -gt 0 ]
    then
        echo "MitkResample done!";
    else
        echo "No file found!";
        exit 1;
    fi


}

for dir in /$WORKFLOW_DIR/$BATCH_NAME/*       # list directories in the form "/tmp/dirname/"
do
        INPUTDIR="$dir/$OPERATOR_IN_DIR"
        OUTPUTDIR="$dir/$OPERATOR_OUT_DIR"
        echo ${INPUTDIR}
        echo ${OUTPUTDIR}
        resampling
done