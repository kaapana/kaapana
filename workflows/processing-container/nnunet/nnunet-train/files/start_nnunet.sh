#bin/bash

set -e

echo "#####################################################################"
echo ""
echo "  Starting nnUNet..."
echo ""
if [ "$MODE" != "training" ] && [ "$MODE" != "inference" ] ; then
    echo ""
    echo "#####################################################################"
    echo ""
    echo "MODE ($MODE) NOT SUPPORTED";
    echo "OPTIONS: training, inference";
    echo ""
    echo "#####################################################################"
    echo ""
    exit 1
fi


echo ""
echo "  MODE: $MODE"
echo ""
if [ "$MODE" = "training" ]; then
    DATASET_DIR="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"

    if ! [ -d "$DATASET_DIR" ]; then
        echo ""
        echo "#####################################################################"
        echo ""
        echo "Error datset-dir not found: ${DATASET_DIR}"
        echo "Can not continue."
        echo ""
        echo "#####################################################################"
        echo ""
        exit 1
    fi
    nnUNet_raw_data_base="$DATASET_DIR"
    echo ""
    echo "  Verify datset itegrity..."
    echo "  TASK_NUM" $TASK_NUM
    echo ""
    # nnUNet_raw_data_base/nnUNet_raw_data/TaskXXX_MYTASK
    nnUNet_plan_and_preprocess -t $TASK_NUM --verify_dataset_integrity

elif [ "$MODE" = "inference" ]; then
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
        python3 -u ./check_empty.py $operator_output_dir
        if [ $? -eq 0 ]; then
            echo "Segmentation found!!"
        else
            echo ""
            echo "#########################################################"
            echo ""
            echo ""
            echo "No segmentation found!"
            echo "The segmentatiion NIFTI has no mask -> no label found."
            echo "Abort"
            echo ""
            echo ""
            echo "#########################################################"
            echo ""
            exit 1
        fi
    done

fi;

echo "########### DONE"
exit 0

