#bin/bash

set -e

PREPROCESS=true
CHECK_INTEGRITY=true

PL=12
PF=8

nnUNet_raw_data_base="$DATASET_DIR"
nnUNet_preprocessed="$DATASET_DIR/nnUNet_preprocessed"
RESULTS_FOLDER="$DATASET_DIR/results"

echo "#######################################################################"
echo "#"
echo "# Starting nnUNet..."
echo "#"
if [ "$MODE" != "training" ] && [ "$MODE" != "inference" ]  && [ "$MODE" != "preprocess" ] ; then
    echo "#"
    echo "#######################################################################"
    echo "#"
    echo "# MODE ($MODE) NOT SUPPORTED";
    echo "# OPTIONS: preprocess, training, inference";
    echo "#"
    echo "#######################################################################"
    echo "#"
    exit 1
fi

DATASET_DIR="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"
if [ "$MODE" == "training" ] || [ "$MODE" == "preprocess" ] && ! [ -d "$DATASET_DIR" ]; then
    echo "#"
    echo "#######################################################################"
    echo "#"
    echo "# Error datset-dir not found: ${DATASET_DIR}"
    echo "# Can not continue."
    echo "#"
    echo "#######################################################################"
    echo "#"
    exit 1
fi

echo "#"
echo "# MODE: $MODE"
echo "#"
if [ "$MODE" = "preprocess" ]; then

    preprocess_processes_low=$PL
    preprocess_processes_full=$PF
    if [ "$CHECK_INTEGRITY" = "True" ] || [ "$CHECK_INTEGRITY" = "true" ]; then
        preprocess_verify="--verify_dataset_integrity"
    else
        preprocess_verify=""
    fi

    if [ "$PREPROCESS" = "True" ] || [ "$PREPROCESS" = "true" ]; then
        preprocess_verify="-no_pp"
    else
        preprocess_verify=""
    fi

    echo "#"
    echo "# Verify dataset itegrity..."
    echo "# TASK_NUM" $TASK_NUM
    echo "#"
    echo "# COMMAND: nnUNet_plan_and_preprocess -t $TASK_NUM -tl $preprocess_processes_low -tf $preprocess_processes_full $preprocess_verify $preprocess_verify"
    echo "#"
    nnUNet_plan_and_preprocess -t $TASK_NUM -tl $preprocess_processes_low -tf $preprocess_processes_full $preprocess_verify $preprocess_verify
    echo "#"
    echo "# Dataset itegrity OK!"
    echo "#"

elif [ "$MODE" = "training" ]; then
    echo "#"
    echo "# Starting training..."
    echo "#"
    echo "# TASK_NUM" $TASK_NUM
    echo "#"
    echo "# COMMAND: nnUNet_train 2d nnUNetTrainerV2 $TASK_NUM 5"
    #nnUNet_train CONFIGURATION TRAINER_CLASS_NAME TASK_NAME_OR_ID FOLD (additional options)
    nnUNet_train 2d nnUNetTrainerV2 $TASK_NUM 5


    echo "#"
    echo "# DONE"

elif [ "$MODE" = "inference" ]; then
    NUM_THREADS_PREPROCESSING="1"
    NUM_THREADS_NIFTISAVE="1"

    shopt -s globstar
    BATCH_COUNT=$(find "$BATCHES_INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)

    if [ $BATCH_COUNT -eq 0 ]; then
    echo "# No batch-data found -> abort."
    exit 1
    else
    echo "# Found $BATCH_COUNT batches."
    fi

    echo "#"
    echo "# BATCHES_INPUT_DIR:" $BATCHES_INPUT_DIR
    ls $BATCHES_INPUT_DIR
    echo "# BATCH_COUNT: " $BATCH_COUNT
    echo "# NUM_THREADS_PREPROCESSING: " $NUM_THREADS_PREPROCESSING
    echo "# NUM_THREADS_NIFTISAVE: " $NUM_THREADS_NIFTISAVE
    echo "#"

    echo "#";
    echo "# Starting batch loop...";
    echo "#";

    for batch_dir in $BATCHES_INPUT_DIR/*
    do

        batch_name=$(basename -- "$batch_dir")
        
        echo "# TASK" $TASK
        echo "# MODEL" $MODEL
        echo "# INPUT_DIRS" $INPUT_DIRS
        echo "# batch_dir" $batch_dir
        echo "# batch_name" $batch_name
        echo "# MODE" $MODE
        echo "#"
        echo "#"
        
        operator_input_dir=${batch_dir}/${OPERATOR_IN_DIR}
        prepare_output_dir=${batch_dir}/${PREP_DIR}
        mkdir -p $prepare_output_dir

        operator_output_dir=${batch_dir}/${OPERATOR_OUT_DIR}
        mkdir -p $operator_output_dir

        if [ "$PREPARATION" = "true" ] ; then
            echo "############# Starting nnUNet file preparation..."
            python3 -u ./preparation.py
            if [ $? -eq 0 ]; then
                echo "# Data preparation successful!"
            else
                echo "# Data preparation failed!"
                exit 1
            fi
        else
            echo "############# nnUNet file preparation is turned off! (PREPARATION: '$PREPARATION')"
            find . -name $operator_input_dir\*.nii* -exec cp {} $prepare_output_dir \;

        fi

        echo "############# Starting nnUNet prediction..."
        #CONFIGURATION can be 2d, 3d_lowres or 3d_fullres        
        nnUNet_predict -t $TASK -i $prepare_output_dir -o $operator_output_dir -m $MODEL --num_threads_preprocessing $NUM_THREADS_PREPROCESSING --num_threads_nifti_save $NUM_THREADS_NIFTISAVE --disable_tta --mode fast --all_in_gpu False
        if [ $? -eq 0 ]; then
            echo "############# Prediction successful!"
        else
            echo "############# Prediction failed!"
            exit 1
        fi
        echo "############# Testing if segmentation is present..."
        python3 -u ./check_empty.py $operator_output_dir
        if [ $? -eq 0 ]; then
            echo "# Segmentation found!!"
        else
            echo "#"
            echo "###########################################################"
            echo "#"
            echo "#"
            echo "# No segmentation found!"
            echo "# The segmentatiion NIFTI has no mask -> no label found."
            echo "# Abort"
            echo "#"
            echo "#"
            echo "###########################################################"
            echo "#"
            exit 1
        fi
    done

fi;

echo "#"
echo "#"
echo "##########################        DONE       ##########################"
echo "#"
echo "#######################################################################"
exit 0

# usage: nnUNet_plan_and_preprocess [-h] [-t TASK_IDS [TASK_IDS ...]]
#                                   [-pl3d PLANNER3D] [-pl2d PLANNER2D] [-no_pp]
#                                   [-tl TL] [-tf TF]
#                                   [--verify_dataset_integrity]

# optional arguments:
#   -h, --help            show this help message and exit
#   -t TASK_IDS [TASK_IDS ...], --task_ids TASK_IDS [TASK_IDS ...]
#                         List of integers belonging to the task ids you wish to
#                         run experiment planning and preprocessing for. Each of
#                         these ids must, have a matching folder 'TaskXXX_' in
#                         the raw data folder
#   -pl3d PLANNER3D, --planner3d PLANNER3D
#                         Name of the ExperimentPlanner class for the full
#                         resolution 3D U-Net and U-Net cascade. Default is
#                         ExperimentPlanner3D_v21. Can be 'None', in which case
#                         these U-Nets will not be configured
#   -pl2d PLANNER2D, --planner2d PLANNER2D
#                         Name of the ExperimentPlanner class for the 2D U-Net.
#                         Default is ExperimentPlanner2D_v21. Can be 'None', in
#                         which case this U-Net will not be configured
#   -no_pp                Set this flag if you dont want to run the
#                         preprocessing. If this is set then this script will
#                         only run the experiment planning and create the plans
#                         file
#   -tl TL                Number of processes used for preprocessing the low
#                         resolution data for the 3D low resolution U-Net. This
#                         can be larger than -tf. Don't overdo it or you will
#                         run out of RAM
#   -tf TF                Number of processes used for preprocessing the full
#                         resolution data of the 2D U-Net and 3D U-Net. Don't
#                         overdo it or you will run out of RAM
#   --verify_dataset_integrity
#                         set this flag to check the dataset integrity. This is
#                         useful and should be done once for each dataset!
