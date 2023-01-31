import os
from os.path import exists
import shutil
from pathlib import Path
from typing import List

import torch
from totalsegmentator.libs import setup_nnunet


def total_segmentator(input_path: Path, output_path: Path, task: str = 'total', fast: bool = False,
                      quiet: bool = False):
    if not torch.cuda.is_available():
        raise ValueError(
            "TotalSegmentator only works with a NVidia CUDA GPU. CUDA not found. " +
            "If you do not have a GPU check out our online tool: www.totalsegmentator.com")

    os.environ["TOTALSEG_WEIGHTS_PATH"] = str("/models/total_segmentator")
    setup_nnunet()

    from totalsegmentator.nnunet import \
        nnUNet_predict_image  # this has to be after setting new env vars

    if task == "total":
        if fast:
            task_id = 256
            resample = 3.0
            trainer = "nnUNetTrainerV2_ep8000_nomirror"
            crop = None
            if not quiet: print("Using 'fast' option: resampling to lower resolution (3mm)")
        else:
            task_id = [251, 252, 253, 254, 255]
            resample = 1.5
            trainer = "nnUNetTrainerV2_ep4000_nomirror"
            crop = None
    elif task == "lung_vessels":
        task_id = 258
        resample = None
        trainer = "nnUNetTrainerV2"
        crop = "lung"
    elif task == "covid":
        task_id = 201
        resample = None
        trainer = "nnUNetTrainerV2"
        crop = "lung"
        print("WARNING: The COVID model finds many types of lung opacity not only COVID. Use with care!")
    elif task == "cerebral_bleed":
        task_id = 150
        resample = None
        trainer = "nnUNetTrainerV2"
        crop = "brain"
    elif task == "hip_implant":
        task_id = 260
        resample = None
        trainer = "nnUNetTrainerV2"
        crop = "pelvis"
    elif task == "coronary_arteries":
        task_id = 503
        resample = None
        trainer = "nnUNetTrainerV2"
        crop = "heart"
        print("WARNING: The coronary artery model does not work very robust. Use with care!")

    model = "3d_fullres"

    # TODO: Subtasks such as lung_vessels or cerebral_bleed require segmentation mask of the respective organ
    folds = [0]  # None
    nnUNet_predict_image(
        input_path, output_path, task_id, model=model, folds=folds, crop=crop, crop_path=output_path, task_name=task,
        trainer=trainer, tta=False, multilabel_image=False, resample=resample
    )

    shutil.copy('seg_info.json', output_path)


batch_folders: List[Path] = sorted([*Path('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME']).glob('*')])

for batch_element_dir in batch_folders:

    element_input_dir = batch_element_dir / os.environ['OPERATOR_IN_DIR']
    element_output_dir = batch_element_dir / os.environ['OPERATOR_OUT_DIR']

    element_output_dir.mkdir(exist_ok=True)

    # The processing algorithm
    print(
        f'Checking {str(element_input_dir)} for nifti files and writing results to {str(element_output_dir)}'
    )
    nifti_files: List[Path] = sorted([*element_input_dir.rglob("*.nii.gz")])

    if len(nifti_files) == 0:
        print("No nifti file found!")
        exit(1)
    else:
        for nifti_file in nifti_files:
            print(f"# running total segmentator")
            
            assert exists(nifti_file.absolute())
            assert exists(element_output_dir.absolute())
            
            try:
                total_segmentator(
                    nifti_file.absolute(),
                    element_output_dir.absolute(),
                    task=os.environ['TASK']
                )
                print("# Successfully processed")
            except Exception as e:
                print("Processing failed with exception: ", e)
                exit(1)
