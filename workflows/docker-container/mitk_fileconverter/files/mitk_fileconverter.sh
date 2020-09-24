#bin/bash
shopt -s globstar
BATCH_COUNT=$(find "$BATCHES_INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)

echo ""
echo "BATCHES_INPUT_DIR:" $BATCHES_INPUT_DIR
echo "BATCH_COUNT: " $BATCH_COUNT
echo ""
echo "CONVERTFROM:" $CONVERTFROM
echo "CONVERTTO:  " $CONVERTTO

if [ "$CONVERTTO" != "nrrd" ] && [ "$CONVERTTO" != "nii" ] && [ "$CONVERTTO" != "nii.gz" ] ; then
    echo "CONVERT-TO-FORMAT ($CONVERTTO) NOT SUPPORTED"
    echo "OPTIONS: nrrd,nii,nii.gz"
    exit 1
fi

echo ""
echo "Starting batch loop..."
echo ""

for batch_dir in $BATCHES_INPUT_DIR/*
do
    batch_input_dir=${batch_dir}/${OPERATOR_IN_DIR}
    batch_output_dir=${batch_dir}/${OPERATOR_OUT_DIR}
    batch_name=$(basename -- "$batch_dir")
    
    echo "batch_dir" $batch_dir
    echo "batch_name" $batch_name
    echo "BATCH INPUT DIR:  " $batch_input_dir
    echo "BATCH OUTPUT DIR: " $batch_output_dir
    echo ""
    
    if [ ! -d "$batch_input_dir" ]; then
        echo "BATCH INPUT DIR does not exists: " $batch_input_dir
        echo "Skipping batch..."
        continue
    fi
    
    loop_counter=0
    # check if no dcm extension is set
    if [[ $CONVERTFROM = *[!\ ]* ]]; then
        extension_query="*.$CONVERTFROM"
    else
        extension_query="**/*"
    fi
    
    shopt -s nullglob
    for file_found in "$batch_input_dir"/$extension_query; do
        filepath=${file_found%/*};
        filename=${file_found##*/};
        
        mkdir -p "$batch_output_dir"
        
        if [ "$CONVERTFROM" == "dcm" ];then
            output_filepath="$batch_output_dir"/"$batch_name"."$CONVERTTO"
        else
            output_filepath="$batch_output_dir"/"${filename/"$CONVERTFROM"/$CONVERTTO}"
        fi
        
        echo ""
        echo "file_found: " $file_found
        echo "output_filepath: " $output_filepath
        echo ""
        
        ((++loop_counter))
        install -Dv / $output_filepath
        $FILECONVERTER -i "$file_found" -o "$output_filepath";
        
        [ ! -f "$output_filepath" ] && { echo "Error: Converted file not found!."; exit 2; }
        if [ -s "$output_filepath" ]
        then
            echo "Converted file found and has some data."
        else
            echo "Converted file found but is empty!"
            rm -rf $output_filepath
            exit 1;
        fi;
        
        file_count=$(find "$batch_output_dir" -maxdepth 1 -name \*.$CONVERTTO | wc -l)
        if [ "$file_count" -gt 1 ]
        then
            echo ""
            echo ""
            echo ""
            echo ""
            echo ""
            echo ""
            echo ""
            echo ""
            echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            echo "########################################          ERROR          ########################################"
            echo ""
            echo "                           Multiple converted files were found!";
            echo "";
            echo "            This typically happens when something is wrong with the DICOM files.";
            echo "                    Like missing volume slides or similar issues.";
            echo ""
            echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            echo "FILE_COUNT: " $file_count
            if [ "$FORCE_SINGLE_FILE" = true ] ; then
                echo "Starting new conversion -> forcing single file output!"
                rm -rf $batch_output_dir/*
                $FILECONVERTER -r 'MITK Simple Volume Importer' -i $f -o $output_filepath;
                
                [ ! -f "$output_filepath" ] && { echo "Error: Converted file not found!."; exit 2; }
                if [ -s "$output_filepath" ]
                then
                    echo "Converted file found and has some data."
                    
                else
                    echo "Converted file found but is empty!"
                    rm -rf $output_filepath
                    exit 1;
                fi;
                
                file_count=$(find $output_dir_path -maxdepth 1 -name \*.$CONVERTTO | wc -l)
                echo "FILE_COUNT: " $file_count
                if [ "$file_count" -gt 1 ]
                then
                    echo "Again more than one files have been found."
                    echo "Exiting!"
                    exit 1
                fi;
            else
                echo "NOT FORCING TO SINGLE FILE! (CAN BE ENABLED BY FORCE_SINGLE_FILE=true -> not recommended)"
                echo "This is considered as an error and the program is terminated!";
                exit 1
            fi;
            
        fi

        if [ "$CONVERTFROM" == "dcm" ];then
            echo "DICOM -> one slice is enough..."
            break
        fi
    done
    
done

if [[ "$loop_counter" -gt 0 ]] ; then
    echo "Fileconverter done!";
    exit 0;
else
    echo "No input file found!";
    exit 1;
fi;