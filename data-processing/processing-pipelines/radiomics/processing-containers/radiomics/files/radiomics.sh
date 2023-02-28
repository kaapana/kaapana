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
        
        # for maskfile in $(find $MASKDIR  -name '*.nrrd' | while read f ); do
        find $MASKDIR  -name '*.nrrd' | while read maskfile; do
            echo $maskfile
        # for maskfile in `find $MASKDIR -type f -name "*.nrrd"`; do
        # for maskfile in $(ls $MASKDIR/*.nrrd | head -1); do
            echo "Maskfile $maskfile"
            if [ "$maskfile" == "bin" ];
            then 
                echo "Could not find mask-file!"
                echo "path: $MASKDIR/*.nrrd"
                exit 1
            fi

            echo "Mask-file found: $maskfile"
            mkdir -p $OUTPUTDIR

            maskfile_name=$(basename "$maskfile")
            seg_name="${maskfile_name/.nrrd/}"  
            seg_name="${seg_name// /_}"  
            echo "Extracteds seg-name $seg_name"

            filename="${filename%.*}";
            xml_filepath=$OUTPUTDIR/$seg_name'_radiomics.xml';
            csv_filepath=$OUTPUTDIR/$seg_name'_radiomics.csv';
            json_filepath=$OUTPUTDIR/$seg_name'_radiomics.json';

            echo "###################################################################### CONFIG"
            echo "#"
            echo "#"
            echo '# xml_filepath: ' $xml_filepath
            echo '# csv_filepath: ' $csv_filepath
            echo "# INPUT-FILE: " $file
            echo "# MASK-DIR: "$MASKDIR/
            echo "# MASKF-FILE: " $maskfile
            echo "#"
            echo "# xml_filepath:  $xml_filepath"
            echo "# csv_filepath:  $csv_filepath"
            echo "# json_filepath: $json_filepath"
            echo "#"

            install -Dv / "$xml_filepath"
            echo "###"
            echo "### COMMAND: /kaapana/app/MitkCLGlobalImageFeatures.sh -i $file -o $csv_filepath -x $xml_filepath -m $maskfile -rm 1 -sp 1 -head 1 -fl-head 1 $PARAMETERS"
            echo "###"
            chmod +x /kaapana/app/MitkCLGlobalImageFeatures.sh
            set -e
            /kaapana/app/MitkCLGlobalImageFeatures.sh -i "$file" -o "$csv_filepath" -x "$xml_filepath" -m "$maskfile" -rm 1 -sp 1 -head 1 -fl-head 1 $PARAMETERS
            
            retVal=$?
            if [ $retVal -ne 0 ]; then
                echo "MitkCLGlobalImageFeatures Error!"
                exit 1;
            else
                echo "MitkCLGlobalImageFeatures DONE!"
                echo "# Converting XML -> JSON ...";
                cat "$xml_filepath" | xq >> $json_filepath
            fi
        done
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


