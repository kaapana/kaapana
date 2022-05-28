# nnUNet_plan_and_preprocess
# nnUNet_train
usage: nnUNet_train [-h] [-val] [-c] [-p P] [--use_compressed_data]
                    [--deterministic] [--npz] [--find_lr] [--valbest] [--fp32]
                    [--val_folder VAL_FOLDER]
                    network network_trainer task fold

positional arguments:
  network
  network_trainer
  task                  can be task name or task id
  fold                  0, 1, ..., 5 or 'all'

optional arguments:
  -h, --help            show this help message and exit
  -val, --validation_only
                        use this if you want to only run the validation
  -c, --continue_training
                        use this if you want to continue a training
  -p P                  plans identifier. Only change this if you created a
                        custom experiment planner
  --use_compressed_data
                        If you set use_compressed_data, the training cases
                        will not be decompressed. Reading compressed data is
                        much more CPU and RAM intensive and should only be
                        used if you know what you are doing
  --deterministic       Makes training deterministic, but reduces training
                        speed substantially. I (Fabian) think this is not
                        necessary. Deterministic training will make you
                        overfit to some random seed. Don't use that.
  --npz                 if set then nnUNet will export npz files of predicted
                        segmentations in the validation as well. This is
                        needed to run the ensembling step so unless you are
                        developing nnUNet you should enable this
  --find_lr             not used here, just for fun
  --valbest             hands off. This is not intended to be used
  --fp32                disable mixed precision training and run old school
                        fp32
  --val_folder VAL_FOLDER
                        name of the validation folder. No need to use this for
                        most people

# nnUNet_export_model_to_zip

  -h, --help        show this help message and exit
  -t T              task name or task id
  -o O              output file name. Should end with .zip
  -m M [M ...]      list of model configurations. Default: 2d 3d_lowres
                    3d_fullres 3d_cascade_fullres. Must be adapted to fit the
                    available models of a task
  -tr TR            trainer class used for 2d 3d_lowres and 3d_fullres.
                    Default: nnUNetTrainerV2
  -trc TRC          trainer class used for 3d_cascade_fullres. Default:
                    nnUNetTrainerV2CascadeFullRes
  -pl PL            nnunet plans identifier. Default: nnUNetPlansv2.1
  --disable_strict  set this if you want to allow skipping missing things
  -f F [F ...]      Folds. Default: 0 1 2 3 4

# nnUNet_install_pretrained_model_from_zip
# nnUNet_download_pretrained_model_by_url

# nnUNet_predict
# nnUNet_print_pretrained_model_info
# nnUNet_download_pretrained_model
# nnUNet_ensemble
# nnUNet_change_trainer_class
# nnUNet_convert_decathlon_task
# nnUNet_determine_postprocessing
# nnUNet_train_DDP
# nnUNet_find_best_configuration
# nnUNet_train_DP
# nnUNet_print_available_pretrained_models
