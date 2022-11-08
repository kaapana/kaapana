import glob
import os
from pathlib import Path

import torch
from totalsegmentator.libs import setup_nnunet, download_pretrained_weights


def total_segmentator(input_path: Path, output_path: Path):
    if not torch.cuda.is_available():
        raise ValueError(
            "TotalSegmentator only works with a NVidia CUDA GPU. CUDA not found. " +
            "If you do not have a GPU check out our online tool: www.totalsegmentator.com")

    setup_nnunet()

    from totalsegmentator.nnunet import \
        nnUNet_predict_image  # this has to be after setting new env vars

    fast = False
    quiet = False
    if fast:
        task_id = 256
        resample = 3.0
        trainer = "nnUNetTrainerV2_ep8000_nomirror"
        if not quiet:
            print(
                "Using 'fast' option: resampling to lower resolution (3mm)"
            )
    else:
        task_id = [251, 252, 253, 254, 255]
        resample = 1.5
        trainer = "nnUNetTrainerV2_ep4000_nomirror"
    model = "3d_fullres"

    if type(task_id) is list:
        for tid in task_id:
            download_pretrained_weights(tid)
    else:
        download_pretrained_weights(task_id)

    folds = [0]  # None
    nnUNet_predict_image(
        input_path, output_path, task_id, model=model,
        folds=folds,
        trainer=trainer, tta=False,
        multilabel_image=True,
        resample=resample
    )


# if args.statistics:
#     if not quiet: print("Calculating statistics...")
#     st = time.time()
#     get_basic_statistics_for_entire_dir(seg, args.input, args.output / "statistics.json", quiet)
#     # get_radiomics_features_for_entire_dir(args.input, args.output, args.output / "statistics_radiomics.json")
#     if not quiet: print(f"  calculated in {time.time()-st:.2f}s")
#
# if args.radiomics:
#     if not quiet: print("Calculating radiomics...")
#     st = time.time()
#     get_radiomics_features_for_entire_dir(args.input, args.output, args.output / "statistics_radiomics.json")
#     if not quiet: print(f"  calculated in {time.time()-st:.2f}s")


# From the template

batch_folders = sorted(
    [f for f in glob.glob(
        os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'],
                     '*'))])

for batch_element_dir in batch_folders:

    element_input_dir = os.path.join(batch_element_dir,
                                     os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir,
                                      os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    # The processing algorithm
    print(
        f'Checking {element_input_dir} for nifti files and writing results to {element_output_dir}')
    nifti_files = sorted(
        glob.glob(os.path.join(element_input_dir, "*.nii.gz"), recursive=True))

    if len(nifti_files) == 0:
        print("No nifti file found!")
        exit(0)
    else:
        for nifti_file in nifti_files:
            print(f"# running total segmentator")
            total_segmentator(
                Path(nifti_file).absolute(),
                Path(element_output_dir).absolute()
            )
            print("# Sucessfully processed")
