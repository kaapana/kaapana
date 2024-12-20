# TODO: change prints to logging

import json
import os
from os import getenv
from pathlib import Path
import ast
from typing import List, Tuple

import nibabel as nib
import numpy as np
import torch
from monai.metrics.meandice import DiceMetric
from monai.metrics.hausdorff_distance import compute_hausdorff_distance
from monai.metrics.surface_distance import compute_average_surface_distance
from monai.metrics.surface_dice import compute_surface_dice

from opensearch_helper import get_ref_series_instance_uid


def get_and_assert_not_none(env_var):
    """Standard checks for parsing env variables"""
    param = getenv(env_var, "None")
    param = param if param.lower() != "none" else None

    assert param is not None, f"ERROR: {env_var} is passed as None, aborting"

    return param


workflow_dir = get_and_assert_not_none("WORKFLOW_DIR")
operator_out_dir = get_and_assert_not_none("OPERATOR_OUT_DIR")
batch_name = get_and_assert_not_none("BATCH_NAME")
batch_test = get_and_assert_not_none("BATCH_TEST")
batch_gt = get_and_assert_not_none("BATCH_GT")
dir_in_test = get_and_assert_not_none("TEST_IN_DIR")
dir_in_gt = get_and_assert_not_none("GT_IN_DIR")
exit_on_error = get_and_assert_not_none("EXIT_ON_ERROR")
eval_metrics_key = get_and_assert_not_none("METRICS_KEY")
label_mapping = get_and_assert_not_none("LABEL_MAPPING")

# array env var
eval_metrics_str = getenv(eval_metrics_key.upper(), "None")
eval_metrics_ast = (
    ast.literal_eval(eval_metrics_str) if eval_metrics_str.lower() != "none" else None
)
assert eval_metrics_ast is not None
eval_metrics: list = list(eval_metrics_ast)


def read_nifti_file(filepath):
    """Read and return the data from a NIFTI file."""
    nifti_img = nib.load(filepath)
    return nifti_img.get_fdata().astype(int)


def calculate_dice_score(gt_mask, pred_mask):
    res = DiceMetric(include_background=False)(pred_mask, gt_mask).numpy()[0]
    res = np.array([v for v in res]).tolist()
    return res


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


def parse_label_mapping_env() -> list[tuple[str, str]]:
    """
    Parses the label_mapping variable from str format to a list of (str,str) tuples
    """

    res = []
    for lm in label_mapping.split(","):
        split_lm = lm.split(":")
        assert (
            len(split_lm) == 2
        ), f"ERROR: expected two labels per mapping, i.e. 'gt_label_x:test_label_y,gt_label_z:test_label_t'. Got {split_lm}"
        # lower strings in label mappings
        split_lm = [lm.lower() for lm in split_lm]
        gt, test = split_lm
        res.append((gt, test))
    return res


def evaluate_segmentation(dataset_map):
    """
    Calculate and return multiple segmentation evaluation metrics.
    """
    print(f"# Evaluate segmentations with {dataset_map=}")

    metrics = {}
    label_pairs = parse_label_mapping_env()

    # for every gt,test pair
    for uid, data in dataset_map.items():
        try:
            print(f"# Calculating metrics for {uid=}, {data=}...")
            gt_path = Path(data["gt_path"])
            test_path = Path(data["test_path"])

            metric = {
                "dice_score": {},
                "surface_dice": {},
                "hausdorff_distance": {},
                "asd": {},
            }

            # Get masks file with names gt_label and test_label
            for gt_label, test_label in label_pairs:
                f_gt = [i for i in gt_path.glob("*") if gt_label in str(i)]
                f_test = [i for i in test_path.glob("*") if test_label in str(i)]
                # should be only one
                if len(f_gt) > 1:
                    raise Exception(
                        f"ERROR: Multiple mask files for ground truth label '{gt_label}' in {data['gt_id']}. Use fuse operator to merge into one."
                    )
                if len(f_test) > 1:
                    raise Exception(
                        f"ERROR: Multiple mask files for ground truth label '{test_label}' in {data['test_id']}. Use fuse operator to merge into one."
                    )
                print(f"# {f_gt=}, {f_test=}")

                # should not be empty
                assert (
                    len(f_gt) > 0
                ), f"Failed to find gt label masks {label_mapping} for {data['gt_id']} under path {gt_path}"
                assert (
                    len(f_test) > 0
                ), f"Failed to find test label masks {label_mapping} for {data['test_id']} under path {test_path}"

                # Read ground truth and test masks
                gt_mask = convert_to_tensor(read_nifti_file(f_gt[0]))
                pred_mask = convert_to_tensor(read_nifti_file(f_test[0]))

                key = f"{gt_label}:{test_label}"
                # Calculate metrics for each mask pair
                if "dice_score" in eval_metrics:
                    print(
                        f"# Calculating dice score for test mask {data['test_id']} ..."
                    )
                    metric["dice_score"][key] = calculate_dice_score(gt_mask, pred_mask)
                if "surface_dice" in eval_metrics:
                    print(
                        f"# Calculating surface dice for test mask {data['test_id']} ..."
                    )
                    metric["surface_dice"][key] = calculate_surface_dice(
                        gt_mask, pred_mask
                    )
                if "hausdorff_distance" in eval_metrics:
                    print(
                        f"# Calculating hausdorff distance for test mask {data['test_id']} ..."
                    )
                    metric["hausdorff_distance"][key] = calculate_hausdorff(
                        gt_mask, pred_mask
                    )
                if "average_surface_distance" in eval_metrics:
                    print(f"# Calculating ASD for test mask {data['test_id']} ...")
                    metric["asd"][key] = calculate_asd(gt_mask, pred_mask)
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

    return metrics


def write_to_out_dir(fname, data):
    full_path = Path(workflow_dir) / operator_out_dir
    full_path.mkdir(parents=True, exist_ok=True)
    file_path = full_path / fname

    print(f"# Writing {fname} in {file_path}")
    with file_path.open("w") as f:
        json.dump(data, f, indent=4)


def run_eval():
    dataset_map = get_dataset_map(write_file=True)
    metrics = evaluate_segmentation(dataset_map)
    write_to_out_dir("metrics.json", metrics)
    write_to_out_dir("dataset_map.json", dataset_map)

    print("# Segmentation evaluation completed.")


if __name__ == "__main__":
    run_eval()
