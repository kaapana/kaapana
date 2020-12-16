# nnUNet_plan_and_preprocess
# nnUNet_train
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


# nnUNet_predict
# nnUNet_print_pretrained_model_info
# nnUNet_download_pretrained_model
# nnUNet_download_pretrained_model_by_url
# nnUNet_ensemble
# nnUNet_install_pretrained_model_from_zip
# nnUNet_change_trainer_class
# nnUNet_convert_decathlon_task
# nnUNet_determine_postprocessing
# nnUNet_train_DDP
# nnUNet_find_best_configuration
# nnUNet_train_DP
# nnUNet_print_available_pretrained_models
