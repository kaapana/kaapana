# TODO: change prints to logging
# TODO: docs for funcs

import json
import os
from os import getenv
from pathlib import Path
import ast

import nibabel as nib
import numpy as np
import torch
from monai.metrics.hausdorff_distance import compute_hausdorff_distance
from monai.metrics.surface_distance import compute_average_surface_distance
from monai.metrics.surface_dice import compute_surface_dice

from opensearch_helper import get_ref_series_instance_uid

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

batch_test = getenv("BATCH_TEST", "None")
batch_test = batch_test if batch_test.lower() != "none" else None
assert batch_test is not None

batch_gt = getenv("BATCH_GT", "None")
batch_gt = batch_gt if batch_gt.lower() != "none" else None
assert batch_gt is not None

dir_in_test = getenv("TEST_IN_DIR", "None")
dir_in_test = dir_in_test if dir_in_test.lower() != "none" else None
assert dir_in_test is not None

dir_in_gt = getenv("GT_IN_DIR", "None")
dir_in_gt = dir_in_gt if dir_in_gt.lower() != "none" else None
assert dir_in_gt is not None

exit_on_error = getenv("EXIT_ON_ERROR", "None")
exit_on_error = exit_on_error if exit_on_error.lower() != "none" else None
assert exit_on_error is not None

eval_metrics_str = getenv("METRICS", "None")
eval_metrics_ast = (
    ast.literal_eval(eval_metrics_str) if eval_metrics_str.lower() != "none" else None
)
assert eval_metrics_ast is not None
eval_metrics: list = list(eval_metrics_ast)


def read_nifti_file(filepath):
    """Read and return the data from a NIFTI file."""
    nifti_img = nib.load(filepath)
    return nifti_img.get_fdata().astype(int)


def calculate_surface_dice(gt_mask, pred_mask, class_thresholds=[0.5]):
    """Calculate the Surface DICE coefficient."""
    # populate num_of_classes times
    # class_thresholds = np.full(gt_mask.shape[1], class_thresholds[0]).tolist()
    
    # for binary seg.
    class_thresholds = [0.5]
    res = compute_surface_dice(
        pred_mask, gt_mask, class_thresholds=class_thresholds, include_background=False
    )
    res = np.array([v.numpy() for v in res]).tolist()
    return res


def calculate_hausdorff(gt_mask, pred_mask):
    res = compute_hausdorff_distance(pred_mask, gt_mask, include_background=False)
    res = np.array([v.numpy() for v in res]).tolist()
    return res


def calculate_asd(gt_mask, pred_mask):
    res = compute_average_surface_distance(
        pred_mask,
        gt_mask,
        include_background=False,
    )
    res = np.array([v.numpy() for v in res]).tolist()
    return res


def get_all_ids(path):
    """Return all folder names under path."""
    ids = [i.name for i in list(path.glob("*")) if i.is_dir()]
    return ids


def get_dataset_map(write_file=True) -> dict:
    """
    Generate a dict that links test data under BATCH_TEST and gt data under BATCH_GT via reference uids.

    Returns:
        dataset_map
        {'<ct_ref_uid>': {
            'test_id': '<test-id>','test_path': '<test-path>',
            'gt_id': '<gt-id>', 'gt_path': '<gt-path>'
        }, ...}
    """

    dataset_map = {}
    if "dataset_map.json" in os.listdir():
        print("# Using existing dataset_map.json")
        with open("dataset_map.json", "r") as f:
            dataset_map = json.load(f)
        return dataset_map

    wf_path = Path(workflow_dir)
    gt_path = wf_path / batch_gt
    test_path = wf_path / batch_test

    print(f"# {gt_path=} , {test_path=}")

    gt_ids = get_all_ids(gt_path)
    test_ids = get_all_ids(test_path)
    print(f"# {gt_ids=} , {test_ids=}")

    # add ct_uid keys with test mask values to map
    for test_id in test_ids:
        ref_uid = get_ref_series_instance_uid(test_id)
        if ref_uid in dataset_map:
            print(f"# ERROR: duplicate id, {ref_uid=} already exists in dataset_map")
            exit(1)
        test_path = str(wf_path / batch_test / test_id / dir_in_test)
        dataset_map[ref_uid] = {"test_id": test_id, "test_path": test_path}

    # add matching ground truth masks of reference CT uids
    for gt_id in gt_ids:
        gt_path = str(wf_path / batch_gt / gt_id / dir_in_gt)
        ref_uid = get_ref_series_instance_uid(gt_id)
        print(f"# {gt_id=} has {ref_uid=}")
        if ref_uid not in dataset_map:
            print(
                f"# WARNING: ground truth data {gt_id=} references a CT {ref_uid=} that is not referenced by any test data"
            )
            dataset_map[ref_uid] = {"gt_id": gt_id, "gt_path": gt_path}
        else:
            dataset_map[ref_uid]["gt_id"] = gt_id
            dataset_map[ref_uid]["gt_path"] = gt_path

    if write_file:
        with open("dataset_map.json", "w") as f:
            json.dump(dataset_map, f, indent=4)

    return dataset_map


def convert_to_tensor(nifti_mask) -> torch.Tensor:
    # convert all non-zero to one
    binary_mask = (nifti_mask > 0).astype(int)
    one_hot_encoded = np.stack([(binary_mask == 0), (binary_mask == 1)], axis=0)
    # add new dim for batch-size for monai funcs
    one_hot_encoded = np.expand_dims(one_hot_encoded, axis=0)
    encoded_tensor = torch.from_numpy(one_hot_encoded)

    return encoded_tensor


def evaluate_segmentation(dataset_map):
    """
    Calculate and return multiple segmentation evaluation metrics.
    """
    print(f"# Evaluate segmentations with {dataset_map=}")

    metrics = {}

    for uid, data in dataset_map.items():
        try:
            print(f"# Calculating metrics for {uid=}, {data=}...")
            gt_path = Path(data["gt_path"])
            test_path = Path(data["test_path"])

            filtered_gt = [
                i for i in gt_path.glob("*") if "combined_masks.nii.gz" in str(i)
            ]
            filtered_test = [
                i for i in test_path.glob("*") if "combined_masks.nii.gz" in str(i)
            ]

            print(f"# {filtered_gt=}, {filtered_test=}")

            # should not be empty
            assert (
                len(filtered_gt) > 0
            ), f"Failed to find combined_masks for {data['gt_id']} under path {gt_path}"
            assert (
                len(filtered_test) > 0
            ), f"Failed to find combined_masks for {data['test_id']} under path {test_path}"

            if len(filtered_gt) > 1:
                print(
                    f"More than one combine_mask.nii.gz files found under path {gt_path}, using the first one"
                )
            if len(filtered_test) > 1:
                print(
                    f"More than one combine_mask.nii.gz files found under path {test_path}, using the first one"
                )

            # Read ground truth and test masks
            gt_mask = convert_to_tensor(read_nifti_file(filtered_gt[0]))
            pred_mask = convert_to_tensor(read_nifti_file(filtered_test[0]))
            print(f"# {gt_mask.shape=}")
            print(f"# {pred_mask.shape=}")

            # Calculate metrics for each mask pair
            metric = {}
            if "surface_dice" in eval_metrics or "dice_score" in eval_metrics:
                print(f"# Calculating surface dice for test mask {data['test_id']} ...")
                metric["surface_dice"] = calculate_surface_dice(gt_mask, pred_mask)
            if "hausdorff_distance" in eval_metrics:
                print(
                    f"# Calculating hausdorff distance for test mask {data['test_id']} ..."
                )
                metric["hausdorff"] = calculate_hausdorff(gt_mask, pred_mask)
            if "average_surface_distance" in eval_metrics:
                print(f"# Calculating ASD for test mask {data['test_id']} ...")
                metric["asd"] = calculate_asd(gt_mask, pred_mask)
            metrics[data["test_id"]] = metric
        except Exception as e:
            print(f"\n# ERROR: during evaluation of test/gt pair {data}")
            print(f"# ERROR: {e}\n")
            if exit_on_error:
                exit(1)
            else:
                print(f"# WARNING: {exit_on_error=} , skipping...\n")

    print("metrics")
    print(metrics)

    # TODO: (optional) calculate avg values for all metrics and add to json as well

    print("# Writing metrics in metrics.json")
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)


dataset_map = get_dataset_map(write_file=True)
evaluate_segmentation(dataset_map)

print("# Segmentation evaluation completed.")
