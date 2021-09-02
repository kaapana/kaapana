#bin/bash

function radiomics {
    echo "Starting Radiomics-Module..."
    Xvfb :99 -screen 0 1024x768x24 &
    export DISPLAY=:99
    exec "$@"

    loop_counter=0
    organ=$(echo "$ORGAN" | awk '{print tolower($0)}')
    echo 'INPUTDIR: '   $INPUTDIR
    echo 'OUTPUTDIR: '  $OUTPUTDIR
    echo 'MASKDIR: '    $MASKDIR
    echo 'PARAMETERS: ' $PARAMETERS

    export BULK="False"

    shopt -s nullglob
    for file in $(find $INPUTDIR  -name '*.nrrd'); do
        ((++loop_counter))
        filename=$(basename -- "$file");
        echo "Image-file found: $file"

        IFS=/ read -a path_array <<< $file
        len_array=${#path_array[@]}
        img_dir="${path_array[$len_array-2]}"
        echo "IMG DIR: " $img_dir
        
        maskfile=$(ls $MASKDIR/*.nrrd | head -1)

        if [ $maskfile == "bin" ];
        then 
            echo "Could not find mask-file!"
            echo "path: $MASKDIR/*.nrrd"
            exit 1
        fi

        echo "Mask-file found: $maskfile"
        mkdir -p $OUTPUTDIR

        maskfile_name=$(basename $maskfile)
        seg_name="${maskfile_name/.nrrd/}"  
        echo "Extracteds seg-name $seg_name"

        filename="${filename%.*}";
        xml_filepath=$OUTPUTDIR/$seg_name'_radiomics.xml';
        csv_filepath=$OUTPUTDIR/$seg_name'_radiomics.csv';

        echo "###################################################################### CONFIG"
        echo ""
        echo ""
        echo ""
        echo 'xml_filepath: ' $xml_filepath
        echo 'csv_filepath: ' $csv_filepath
        echo "INPUT-FILE: " $file
        echo "MASK-DIR: "$MASKDIR/
        echo "MASKF-FILE: " $maskfile

        install -Dv / "$xml_filepath"
        echo "###"
        echo "### COMMAND: /src/MitkCLGlobalImageFeatures.sh -i $file -o $csv_filepath -x $xml_filepath -m $maskfile -rm 1 -sp 1 -head 1 -fl-head 1 $PARAMETERS"
        echo "###"
        /src/MitkCLGlobalImageFeatures.sh -i "$file" -o "$csv_filepath" -x "$xml_filepath" -m "$maskfile" -rm 1 -sp 1 -head 1 -fl-head 1 $PARAMETERS
        # /src/MitkCLGlobalImageFeatures.sh -i "$file" -o "$csv_filepath" -x "$xml_filepath" -m "$maskfile" -rm 1 -sp 1 -head 1 -fl-head 1 -fo 1 -cooc 1
        
        retVal=$?
        if [ $retVal -ne 0 ]; then
            echo "MitkCLGlobalImageFeatures Error!"
            exit 1;
        else
            echo "MitkCLGlobalImageFeatures DONE!"
        fi
    done

    if [ "$loop_counter" -gt 0 ]
    then
        echo "radiomics done!";
    else
        echo "No file found!";
        exit 1;
    fi


}

for dir in /$WORKFLOW_DIR/$BATCH_NAME/*       # list directories in the form "/tmp/dirname/"
do
        INPUTDIR="$dir/$OPERATOR_IN_DIR"
        OUTPUTDIR="$dir/$OPERATOR_OUT_DIR"
        MASKDIR="$dir/$MASK_OPERATOR_DIR"
        echo ${INPUTDIR}
        echo ${OUTPUTDIR}
        echo ${MASKDIR}
        radiomics
done


