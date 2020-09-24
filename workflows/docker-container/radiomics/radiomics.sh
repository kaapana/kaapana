#bin/bash

echo "Starting Radiomics-Module..."
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99
exec "$@"

for dir in /$WORKFLOW_DIR/$BATCH_NAME/*
do
    ELEMENT_INPUT_DIR="$dir/$OPERATOR_IN_DIR"
    ELEMENT_OUTPUT_DIR="$dir/$OPERATOR_OUT_DIR"
    ELEMENT_MASK_DIR="$dir/$MASK_OPERATOR_DIR"

    echo 'ELEMENT_INPUT_DIR: ' $ELEMENT_INPUT_DIR
    echo 'ELEMENT_OUTPUT_DIR: ' $ELEMENT_OUTPUT_DIR
    echo 'ELEMENT_MASK_DIR: ' $ELEMENT_MASK_DIR

    loop_counter=0
    shopt -s nullglob
    for maskfile in $(find $ELEMENT_MASK_DIR  -name '*.nrrd'); do
        ((++loop_counter))

        dcmfile=$(ls $ELEMENT_INPUT_DIR/*.nrrd | head -1)
        
        filename=$(basename -- "$dcmfile");
        echo "File found: $dcmfile"

        IFS=/ read -a path_array <<< $dcmfile
        len_array=${#path_array[@]}
        
        if [ $dcmfile == "bin" ];
        then 
            echo "Could not find dcm-file!"
            echo "path: $ELEMENT_INPUT_DIR/*.nrrd"
            exit 1
        fi

        echo "Mkdir $ELEMENT_OUTPUT_DIR"
        mkdir -p $ELEMENT_OUTPUT_DIR

        regex="-(.+)\.nrrd"

        if [[ $maskfile =~ $regex ]]; then
            seg_name=${BASH_REMATCH[1]}
        else
            echo "unable to parse string $maskfile"
        fi

        echo "Seg name $seg_name"


        filename="${filename%.*}";
        csv_filepath=$ELEMENT_OUTPUT_DIR/$seg_name'_radiomics.csv';
        json_filepath=$ELEMENT_OUTPUT_DIR/$seg_name'_radiomics.json';
        
        sleep 5
        echo "###################################################################### CONFIG"
        echo ""
        echo ""
        echo ""
        echo 'csv_filepath: ' $csv_filepath
        echo "INPUT-FILE: " $dcmfile
        echo "MASKF-FILE: " $maskfile
        
        install -Dv / $csv_filepath
        
        /opt/bin/MitkCLGlobalImageFeatures -i $dcmfile -o $csv_filepath -m $maskfile -rm 1 -sp 1 -head 1 -fl-head 1 -fo 1 -cooc 1    
        
        retVal=$?
        if [ $retVal -ne 0 ]; then
            echo "MitkCLGlobalImageFeatures Error!"
            exit 1;
        else
            echo "MitkCLGlobalImageFeatures DONE!"
        fi
        
        echo "CONVERTING CSV TO JSON..."
        export "CSV_FILE"=$csv_filepath
        export "JSON_FILE"=$json_filepath
        python -u /radiomics.py
        retVal=$?
        if [ $retVal -ne 0 ]; then
            echo "Error in: radiomics.py !"
            exit 1;
        else
            echo "JSON generated!"
        fi
        
        [ ! -f "$json_filepath" ] && { echo "Error: Result JSON not found!."; exit 2; }
        if [ -s "$json_filepath" ]
        then
            echo "Result JSON found and has some data."
            
        else
            echo "Result JSON found but is empty!"
            rm -rf $json_filepath
            exit 1;
        fi
        
    done

    if [ "$loop_counter" -gt 0 ]
    then
        echo "radiomics done!";
    else
        echo "No file found!";
        exit 1;
    fi
done
