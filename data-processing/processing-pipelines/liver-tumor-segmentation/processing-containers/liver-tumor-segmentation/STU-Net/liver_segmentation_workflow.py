from nnunetv2.paths import nnUNet_results
import torch
from batchgenerators.utilities.file_and_folder_operations import join
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
import json
import os

def execute(input_file, output_file):
    input_folder = input_file[:input_file.rfind('/') + 1]
    os.rename(input_file, f"{input_folder}/test_image_0000.nii.gz")
    output_folder = output_file[:output_file.rfind('/') + 1]
    info = {"seg_info": [{"label_int": "1", "label_name": "liver"}, {"label_int":"2", "label_name": "tumor"}]}
    json_object = json.dumps(info, indent=4)
    with open(f"{output_folder}/info.json", "w") as outfile:
        outfile.write(json_object)
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=False,
        use_mirroring=False,
        device=torch.device('cpu'),
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=True
    )
    # initializes the network architecture, loads the checkpoint
    predictor.initialize_from_trained_model_folder(
        join(nnUNet_results, 'Dataset123_ATLAS/STUNetTrainer_base_ft__nnUNetPlans__3d_fullres'),
        use_folds=(0, ),
        checkpoint_name='checkpoint_best.pth',
    )
    # variant 1: give input and output folders
    predictor.predict_from_files(input_folder,
                                 [output_file],
                                 save_probabilities=False, overwrite=False,
                                 num_processes_preprocessing=2, num_processes_segmentation_export=2,
                                 folder_with_segs_from_prev_stage=None, num_parts=1, part_id=0)
    os.rename(f"{input_folder}/test_image_0000.nii.gz", input_file)
