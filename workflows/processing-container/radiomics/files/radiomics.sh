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
        echo "File found: $file"

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

        echo "Mkdir $OUTPUTDIR"
        mkdir -p $OUTPUTDIR


        regex="-(.+)\.nrrd"

        if [[ $maskfile =~ $regex ]]; then
            seg_name=${BASH_REMATCH[1]}
        else
            echo "unable to parse string $maskfile"
        fi

        echo "Seg name $seg_name"


        filename="${filename%.*}";
        xml_filepath=$OUTPUTDIR/$seg_name'_radiomics.xml';
        csv_filepath=$OUTPUTDIR/$seg_name'_radiomics.csv';

        sleep 5
        echo "###################################################################### CONFIG"
        echo ""
        echo ""
        echo ""
        echo 'xml_filepath: ' $xml_filepath
        echo 'csv_filepath: ' $csv_filepath
        echo "INPUT-FILE: " $file
        echo "MASK-DIR: "$MASKDIR/
        echo "MASKF-FILE: " $maskfile
        echo "Creating DCM_UID: " $img_dir
        echo "$img_dir" > $OUTPUTDIR/dcm_uid.txt

        dcm_uid=$(cat $OUTPUTDIR/dcm_uid.txt)
        if [ -z "$dcm_uid" ];
        then 
            echo "dcm_uid.txt not found!"
            echo "Path: " $OUTPUTDIR/dcm_uid.txt
            exit 1
        fi

        install -Dv / $xml_filepath

        /src/MitkCLGlobalImageFeatures.sh -i $file -o $csv_filepath -x $xml_filepath -m $maskfile -rm 1 -sp 1 -head 1 -fl-head 1 $PARAMETERS
        # /src/MitkCLGlobalImageFeatures.sh -i $file -o $csv_filepath -x $xml_filepath -m $maskfile -rm 1 -sp 1 -head 1 -fl-head 1 -fo 1 -cooc 1
        
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


