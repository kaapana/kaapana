#bin/bash

NUM_THREADS_PREPROCESSING="1"
NUM_THREADS_NIFTISAVE="1"

shopt -s globstar
BATCH_COUNT=$(find "$BATCHES_INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)

if [ $BATCH_COUNT -eq 0 ]; then
  echo "No batch-data found -> abort."
  exit 1
else
  echo "Found $BATCH_COUNT batches."
fi

echo ""
echo "BATCHES_INPUT_DIR:" $BATCHES_INPUT_DIR
ls $BATCHES_INPUT_DIR
echo "BATCH_COUNT: " $BATCH_COUNT
echo "NUM_THREADS_PREPROCESSING: " $NUM_THREADS_PREPROCESSING
echo "NUM_THREADS_NIFTISAVE: " $NUM_THREADS_NIFTISAVE
echo ""

if [ "$MODE" != "train" ] && [ "$MODE" != "predict" ] ; then
    echo "MODE ($MODE) NOT SUPPORTED";
    echo "OPTIONS: train, predict";
    exit 1
fi

echo "";
echo "Starting batch loop...";
echo "";

for batch_dir in $BATCHES_INPUT_DIR/*
do

    batch_name=$(basename -- "$batch_dir")
    
    echo "TASK" $TASK
    echo "MODEL" $MODEL
    echo "INPUT_DIRS" $INPUT_DIRS
    echo "batch_dir" $batch_dir
    echo "batch_name" $batch_name
    echo "MODE" $MODE
    echo ""
    echo ""
    
    if [ "$MODE" == "predict" ]; then
        echo "Mode == predict!"

        operator_input_dir=${batch_dir}/${OPERATOR_IN_DIR}
        prepare_output_dir=${batch_dir}/${PREP_DIR}
        mkdir -p $prepare_output_dir

        operator_output_dir=${batch_dir}/${OPERATOR_OUT_DIR}
        mkdir -p $operator_output_dir

        if [ "$PREPARATION" = "true" ] ; then
            echo "########### Starting nnUNet file preparation..."
            python3 -u ./preparation.py
            if [ $? -eq 0 ]; then
                echo "Data preparation successful!"
            else
                echo "Data preparation failed!"
                exit 1
            fi
        else
            echo "########### nnUNet file preparation is turned off! (PREPARATION: '$PREPARATION')"
            find . -name $operator_input_dir\*.nii* -exec cp {} $prepare_output_dir \;

        fi

        echo "########### Starting nnUNet prediction..."

        #CONFIGURATION can be 2d, 3d_lowres or 3d_fullres        
        nnUNet_predict -t $TASK -i $prepare_output_dir -o $operator_output_dir -m $MODEL --num_threads_preprocessing $NUM_THREADS_PREPROCESSING --num_threads_nifti_save $NUM_THREADS_NIFTISAVE --disable_tta --mode fast --all_in_gpu False
        if [ $? -eq 0 ]; then
            echo "########### Prediction successful!"
        else
            echo "########### Prediction failed!"
            exit 1
        fi
        echo "########### Testing if segmentation is present..."
        python3 -u ./check_empty.py
        if [ $? -eq 0 ]; then
            echo "Segmentation found!!"
        else
            echo "No segmentation found!"
            echo "The segmentatiion NIFTI has no mask -> no label found."
            echo "Abort"
            exit 1
        fi

    elif [ "$MODE" == "train" ]; then
        echo "Mode == train!"
    else
        echo "Mode '$MODE' not recognized"
    fi

    echo "########### DONE"
    exit 0
    
done

# if [[ "$loop_counter" -gt 0 ]] ; then
#     echo "Fileconverter done!";
#     exit 0;
# else
#     echo "No input file found!";
#     exit 1;
# fi;




