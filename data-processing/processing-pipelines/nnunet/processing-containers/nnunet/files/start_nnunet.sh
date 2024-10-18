#bin/bash

set -e

export OMP_THREAD_LIMIT=1
export OMP_NUM_THREADS=1

# disable stdout/stderr buffer  
export PYTHONUNBUFFERED=1

TASK_NUM=$(echo "$TASK" | cut -f1 -d"_" | tr -dc '0-9')

echo "#######################################################################"
echo "#"
echo "# Starting nnUNet..."
echo "#"
echo "# MODE:     $MODE";
echo "# TASK:     $TASK";
echo "# TASK_NUM: $TASK_NUM";
echo "#"

if [ "$MODE" = "preprocess" ]; then
    export nnUNet_raw="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/nnUNet_raw"
    export nnUNet_preprocessed="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/nnUNet_preprocessed"
    export nnUNet_results="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/results"
    
    echo "#"
    echo "# Starting preprocessing..."
    echo "#"
    
    if [ "$PREP_INCREMENT_STEP" = "all" ] || [ "$PREP_INCREMENT_STEP" = "to_dataset_properties" ]; then
        echo "#"
        echo "# Starting create_dataset..."
        echo "#"
        python3 -u ./create_dataset.py
    fi

    if [ ! -z "$MODEL" ]; then
        if [ "$MODEL" == "3d_fullres" ]; then
            number_processes=$PREP_TF
        elif [ "$MODEL" == "3d_lowres" ]; then
            number_processes=$PREP_TL
        fi
    else
        number_processes=""
    fi

    if [ "$PREP_CHECK_INTEGRITY" = "True" ] || [ "$PREP_CHECK_INTEGRITY" = "true" ]; then
        preprocess_verify="--verify_dataset_integrity"
    else
        preprocess_verify=""
    fi
    
    if [ "$PREP_PREPROCESS" = "True" ] || [ "$PREP_PREPROCESS" = "true" ]; then
        preprocess=""
    else
        preprocess="-no_pp"
    fi

    if ! [ -z "$PLAN_NETWORK_PLANNER" ]; then
        experiment_planner=$PLAN_NETWORK_PLANNER
    else
        experiment_planner="nnUNetPlannerResEncM"
    fi

    if ! [ -z "$PRETRAINED_WEIGHTS" ]; then
        experiment_planner_pretrain="-pl3d ExperimentPlanner3D_v21_Pretrained"
        plans_path=$(dirname "$PRETRAINED_WEIGHTS")
        overwrite_plans="-overwrite_plans /models/nnUNet/$plans_path/plans.pkl"   
        overwrite_plans_identifier="-overwrite_plans_identifier TRANSFER_TRIAL"
    else
        experiment_planner_pretrain=""
        overwrite_plans=""
    fi

    echo "#"
    echo "# PREPROCESS:             $PREP_PREPROCESS";
    echo "# PREP_INCREMENT_STEP:    $PREP_INCREMENT_STEP";
    echo "# CHECK_INTEGRITY:        $PREP_CHECK_INTEGRITY";
    echo "#"
    echo "# OMP_THREAD_LIMIT:       $OMP_THREAD_LIMIT";
    echo "# OMP_NUM_THREADS:        $OMP_NUM_THREADS";
    echo "# PREP_TL:                $PREP_TL";
    echo "# PREP_TF:                $PREP_TF";
    echo "#"
    echo "# NIFTI_DIRS:             $INPUT_MODALITY_DIRS";
    echo "# LABEL_DIR:              $PREP_LABEL_DIRS";
    echo "# MODALITIES:             $PREP_MODALITIES";
    echo "#"
    echo "# nnUNet_raw:             $nnUNet_raw";
    echo "# nnUNet_preprocessed:    $nnUNet_preprocessed";
    echo "# nnUNet_results:         $nnUNet_results";
    echo "#"
    echo "# PLANNED MODEL:          $MODEL";
    echo "# PLANNER:                $PLAN_NETWORK_PLANNER";
    echo "#"
    echo "# PRE-TRAINED WEIGHTS:    $PRETRAINED_WEIGHTS";
    echo "#"
    echo "#"
    echo "# COMMAND:     nnUNetv2_plan_and_preprocess -d $TASK_NUM -pl $PLAN_NETWORK_PLANNER -c $MODEL -np $number_processes --increment_step $PREP_INCREMENT_STEP $preprocess $preprocess_verify $experiment_planner_pretrain $overwrite_plans $overwrite_plans_identifier"
    echo "#"
    nnUNetv2_plan_and_preprocess -d $TASK_NUM -pl $PLAN_NETWORK_PLANNER -c $MODEL -np $number_processes --increment_step $PREP_INCREMENT_STEP $preprocess $preprocess_verify $experiment_planner_pretrain $overwrite_plans $overwrite_plans_identifier
    echo "#"
    echo "# Dataset itegrity OK!"
    echo "#"
    
elif [ "$MODE" = "training" ]; then
    export nnUNet_raw="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"
    export nnUNet_preprocessed="$nnUNet_raw/nnUNet_preprocessed"
    export nnUNet_results="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/results"
    
    TENSORBOARD_DIR="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/tensorboard"

    echo "#"
    echo "# Starting training..."
    echo "#"

    if [ ! -z "$PLAN_NETWORK_PLANNER" ]; then
        if [ "$PLAN_NETWORK_PLANNER" == "nnUNetPlannerResEncM" ]; then
            plans="nnUNetResEncUNetMPlans"
        elif [ "$PLAN_NETWORK_PLANNER" == "nnUNetPlannerResEncL" ]; then
            plans="nnUNetResEncUNetLPlans"
        elif [ "$PLAN_NETWORK_PLANNER" == "nnUNetPlannerResEncXL" ]; then
            plans="nnUNetResEncUNetXLPlans"
        else
            plans="nnUNetResEncUNetMPlans"
        fi
    else
        plans="nnUNetResEncUNetMPlans"
    fi
    
    if ! [ -z "$PRETRAINED_WEIGHTS" ]; then
        pretrain="-pretrained_weights /models/nnUNet/$PRETRAINED_WEIGHTS/model_final_checkpoint.model"
        pretrained_plan="-p nnUNetPlans_pretrained_TRANSFER_TRIAL"
    else
        pretrain=""
        pretrained_plan=""
    fi

    if [ "$TRAIN_CONTINUE" = "True" ] || [ "$TRAIN_CONTINUE" = "true" ]; then
        continue="--c"
        echo "WARNING: --continue-training is set, ignoring pretrained_weights"
    else
        continue=""
    fi
    
    if [ "$FP32" = "True" ] || [ "$FP32" = "true" ]; then
        fp32="--fp32"
    else
        fp32=""
    fi
    if [ "$TRAIN_NPZ" = "True" ] || [ "$TRAIN_NPZ" = "true" ]; then
        npz="--npz"
    else
        npz=""
    fi
    if [ "$TRAIN_DISABLE_POSTPROCESSING" = "True" ] || [ "$TRAIN_DISABLE_POSTPROCESSING" = "true" ]; then
        disable_postprocessing="--disable_postprocessing_on_folds"
    else
        disable_postprocessing=""
    fi


    echo "#"
    echo "# FOLD:                       $TRAIN_FOLD";
    echo "# TASK:                       $TASK";
    echo "# MODEL:                      $MODEL";
    echo "# NETWORK_TRAINER:            $TRAIN_NETWORK_TRAINER";
    echo "# PLANS:                      $plans";
    echo "# FP32:"                      $FP32;
    echo "#"
    echo "# MAX_EPOCHS:                 $TRAIN_MAX_EPOCHS";
    echo "# EPOCHS_PER_ROUND:           $EPOCHS_PER_ROUND";
    echo "# NUM_BATCHES_PER_EPOCH:      $NUM_BATCHES_PER_EPOCH";
    echo "# NUM_VAL_BATCHES_PER_EPOCH:  $NUM_VAL_BATCHES_PER_EPOCH";
    echo "#"
    echo "# nnUNet_raw:                 $nnUNet_raw"
    echo "# nnUNet_preprocessed:        $nnUNet_preprocessed"
    echo "# nnUNet_results:             $nnUNet_results"
    echo "# TENSORBOARD_DIR:            $TENSORBOARD_DIR"
    echo "#"
    echo "# TRAIN_CONTINUE:             $TRAIN_CONTINUE"
    echo "# TRAIN_NPZ:                  $TRAIN_NPZ"
    echo "# PRETRAINED_WEIGHTS:         $PRETRAINED_WEIGHTS"
    echo "#"
    echo "# COMMAND: nnUNetv2_train $TASK_NUM $MODEL $TRAIN_FOLD -p $plans -tr $TRAIN_NETWORK_TRAINER $pretrained_plan $pretrain $fp32 $npz $continue"
    nnUNetv2_train $TASK_NUM $MODEL $TRAIN_FOLD -p $plans -tr $TRAIN_NETWORK_TRAINER $pretrained_plan $pretrain $fp32 $npz $continue
    
    echo "#"
    echo "# DONE"
    
elif [ "$MODE" = "inference" ]; then
    python3 -u ./simple_predict.py
    echo "#"
    
elif [ "$MODE" = "ensemble" ]; then
    echo "#"
    echo "# Starting ensemble..."
    echo "#"

    python3 -u ./ensemble.py
    echo "#"
    
    
elif [ "$MODE" = "identify-best" ]; then
    export nnUNet_raw="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"
    export nnUNet_preprocessed="$nnUNet_raw/nnUNet_preprocessed"
    export nnUNet_results="/$WORKFLOW_DIR/$OPERATOR_IN_DIR/results"
    # export nnUNet_results="$nnUNet_raw/results"

    echo "#"
    echo "# Starting identify-best..."
    echo "#"
    echo "#"
    echo "# nnUNet_raw:  $nnUNet_raw"
    echo "# nnUNet_preprocessed:   $nnUNet_preprocessed"
    echo "# nnUNet_results:        $nnUNet_results"
    echo "#"
    echo "# FOLD:                  $TRAIN_FOLD"
    echo "# TASK:                  $TASK"
    echo "# MODEL:                 $MODEL"
    echo "# TRAIN_NETWORK_TRAINER: $TRAIN_NETWORK_TRAINER"
    echo "# model_output_path:     $model_output_path"
    echo "#"
    echo "#"

    # models="2d 3d_fullres 3d_lowres 3d_cascade_fullres"

    if [ "$TRAIN_STRICT" = "True" ] || [ "$TRAIN_STRICT" = "true" ]; then
        strict="--strict"
    else
        strict=""
    fi

    echo "# COMMAND: nnUNetv2_find_best_configuration -m $MODEL -t $TASK_NUM $strict"
    nnUNetv2_find_best_configuration -m $MODEL -t $TASK_NUM $strict

    echo "#"
    echo "# DONE"

elif [ "$MODE" = "zip-model" ]; then
    export nnUNet_raw="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"
    export nnUNet_preprocessed="$nnUNet_raw/nnUNet_preprocessed"
    export nnUNet_results="$nnUNet_raw/results"
    
    mkdir -p "/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/"
    TIMESTAMP=`date +%Y-%m-%d_%H-%M`
    model_output_path="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/nnunet_$TASK_$MODEL_$TIMESTAMP.zip"
    
    echo "#"
    echo "# Starting export-model..."
    echo "#"
    echo "#"
    echo "# nnUNet_raw:  $nnUNet_raw"
    echo "# nnUNet_preprocessed:   $nnUNet_preprocessed"
    echo "# nnUNet_results:        $nnUNet_results"
    echo "#"
    echo "# FOLD:                  $TRAIN_FOLD"
    echo "# TASK:                  $TASK"
    echo "# MODEL:                 $MODEL"
    echo "# TRAIN_NETWORK_TRAINER: $TRAIN_NETWORK_TRAINER"
    echo "# model_output_path:     $model_output_path"
    echo "#"
    echo "# COMMAND: zip -r $model_output_path $nnUNet_results/nnUNet/"
    echo "#"
    zip -r "$model_output_path" "$nnUNet_results/nnUNet/"
    
    echo "# DONE"

elif [ "$MODE" = "export-model" ]; then
    export nnUNet_raw="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"
    export nnUNet_preprocessed="$nnUNet_raw/nnUNet_preprocessed"
    export nnUNet_results="$nnUNet_raw/results"
    
    mkdir -p "/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/"
    model_output_path="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/nnunet_model_$MODEL.zip"
    
    echo "#"
    echo "# Starting export-model..."
    echo "#"
    echo "#"
    echo "# nnUNet_raw:  $nnUNet_raw"
    echo "# nnUNet_preprocessed:   $nnUNet_preprocessed"
    echo "# nnUNet_results:        $nnUNet_results"
    echo "#"
    echo "# FOLD:                  $TRAIN_FOLD"
    echo "# TASK:                  $TASK"
    echo "# MODEL:                 $MODEL"
    echo "# TRAIN_NETWORK_TRAINER: $TRAIN_NETWORK_TRAINER"
    echo "# model_output_path:     $model_output_path"
    echo "#"
    echo "#"
    echo "# COMMAND: nnUNetv2_export_model_to_zip -t $TASK -m $MODEL -tr $TRAIN_NETWORK_TRAINER -o $model_output_path "
    echo "#"
    echo "# DONE"
    nnUNetv2_export_model_to_zip -t $TASK -m $MODEL -tr $TRAIN_NETWORK_TRAINER -o $model_output_path -f 0 1 2 3 4
    
elif [ "$MODE" = "install-model" ]; then
    export nnUNet_raw="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"
    export nnUNet_preprocessed="$nnUNet_raw/nnUNet_preprocessed"
    export nnUNet_results="$MODELS_DIR"
    
    mkdir -p "/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/"
    model_output_path="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR/nnunet_model_$MODEL.zip"
    
    echo "#"
    echo "# Starting install-model..."
    echo "#"
    echo "#"
    echo "# nnUNet_raw:  $nnUNet_raw"
    echo "# nnUNet_preprocessed:   $nnUNet_preprocessed"
    echo "# nnUNet_results:        $nnUNet_results"
    echo "#"
    echo "# FOLD:                  $TRAIN_FOLD"
    echo "# TASK:                  $TASK"
    echo "# MODEL:                 $MODEL"
    echo "# TRAIN_NETWORK_TRAINER: $TRAIN_NETWORK_TRAINER"
    echo "# model_output_path:     $model_output_path"
    echo "#"
    echo "#"
    
    cd "/$WORKFLOW_DIR/$OPERATOR_IN_DIR"

    shopt -s nullglob
    for MODEL_PATH in *.zip; do
        echo "Found zip-file: $MODEL_PATH"
        echo "Installing: nnUNetv2_install_pretrained_model_from_zip $MODEL_PATH"
        nnUNetv2_install_pretrained_model_from_zip $MODEL_PATH
        
    done
    echo "#"
    echo "# DONE"
    
fi;

echo "#"
echo "#"
echo "##########################        DONE       ##########################"
echo "#"
echo "#######################################################################"
exit 0
