# TODO: change prints to logging
# TODO: docs for funcs

import json
from os import getenv
from pathlib import Path

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


def read_nifti_file(filepath):
    """Read and return the data from a NIFTI file."""
    nifti_img = nib.load(filepath)
    return nifti_img.get_fdata().astype(int)


def one_hot_encode(tensor, num_classes=2):
    """One-hot encode the binary mask tensor."""
    shape = tensor.shape
    one_hot = torch.zeros((num_classes,) + shape, dtype=torch.bool)
    for c in range(num_classes):
        one_hot[c] = tensor == c
    return one_hot


def calculate_surface_dice(gt_mask, pred_mask, class_thresholds=[0.5]):
    """Calculate the Surface DICE coefficient."""
    return compute_surface_dice(
        pred_mask, gt_mask, class_thresholds=class_thresholds, include_background=True
    )


def calculate_volumetric_similarity(gt_mask, pred_mask):
    """Calculate the Volumetric Similarity."""
    intersection = np.logical_and(gt_mask, pred_mask).sum()
    volume_sum = gt_mask.sum() + pred_mask.sum()
    if volume_sum == 0:
        return 1
    else:
        return (2.0 * intersection) / volume_sum


def get_all_ids(path):
    """Return all folder names under path."""
    ids = [i.name for i in list(path.glob("*")) if i.is_dir()]
    return ids


def create_dataset_map(write_file=True) -> dict:
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

    wf_path = Path(workflow_dir)
    gt_path = wf_path / batch_gt
    test_path = wf_path / batch_test

    print(f"{gt_path=} , {test_path=}")

    gt_ids = get_all_ids(gt_path)
    test_ids = get_all_ids(test_path)
    print(f"{gt_ids=} , {test_ids=}")

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
        print(f"{gt_id=} has {ref_uid=}")
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
    # TODO: find a way to get label_int label_info pairs similar to seg_info.json in seg-check
    max_label_encoding = 1

    # divide by label int
    non_zero = nifti_mask[np.nonzero(nifti_mask)]
    unique = np.unique(non_zero)
    if len(unique) == 1:
        print(f"single label {unique[0]} found")
        nifti_mask = nifti_mask / unique[0]
    else:
        # TODO: remove this exit when max_label_encoding no longer assumes binary segmentation
        print(f"multiple labels {unique} found, aborting")
        exit(1)

    print(f"{nifti_mask.shape=}")

    # one hot encoding
    one_hot_encoded = (
        (np.arange(max_label_encoding + 1) == nifti_mask[..., None])
        .astype(int)
        .transpose()
    )
    one_hot_encoded = np.expand_dims(one_hot_encoded, axis=0)
    encoded_tensor = torch.from_numpy(one_hot_encoded)

    return encoded_tensor


def evaluate_segmentation(dataset_map, filter_keyword=None):
    """
    Calculate and return multiple segmentation evaluation metrics.
    """
    # TODO: (optional) add metrics selection

    print(f"Evaluate segmentations with {dataset_map=} and {filter_keyword=}")

    metrics = {
        "surface_dice": [],
        "vol_similarity": [],
        "hausdorff": [],
        "asd": [],
    }

    for uid, data in dataset_map.items():
        print(f"Calculating metrics for {uid=}, {data=}...")
        gt_path = Path(data["gt_path"])
        test_path = Path(data["test_path"])

        # TODO: add here label name based filters
        filtered_gt = [
            i
            for i in gt_path.glob("*")
            if (filter_keyword is not None) and filter_keyword in str(i)
        ]
        filtered_test = [
            i
            for i in test_path.glob("*")
            if (filter_keyword is not None) and filter_keyword in str(i)
        ]

        print(f"{filtered_gt=}, {filtered_test=}")

        assert len(filtered_gt) == 1
        assert len(filtered_test) == 1

        # Read the ground truth and test masks
        gt_mask = read_nifti_file(filtered_gt[0])
        pred_mask = read_nifti_file(filtered_test[0])

        # Calculate metrics for each mask pair
        metrics["surface_dice"].append(calculate_surface_dice(gt_mask, pred_mask))
        metrics["vol_similarity"].append(
            calculate_volumetric_similarity(gt_mask, pred_mask)
        )
        metrics["hausdorff"].append(
            compute_hausdorff_distance(pred_mask, gt_mask, include_background=False)
        )
        metrics["asd"].append(
            compute_average_surface_distance(
                pred_mask,
                gt_mask,
                include_background=False,
            )[0]
        )

    for metric_name, values in metrics.items():
        if values:
            average_value = np.mean(values)
            print(f"{metric_name}: {average_value:.4f}")

    print("Writing metrics in metrics.json")
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)


dataset_map = create_dataset_map(write_file=True)
evaluate_segmentation(dataset_map)
print("Successfully evaluated segmentations.")