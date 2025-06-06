import os
from os import getenv, remove
from os.path import join, exists, dirname, basename
from glob import glob
from shutil import copy2, move, rmtree
from pathlib import Path
import shutil
import nibabel as nib
import numpy as np
import json
from pydicom.uid import generate_uid
from typing import Tuple
import sparse
from kaapanapy.logger import get_logger
import logging


logger = get_logger(__name__, logging.DEBUG)

# For multiprocessing
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run

execution_timeout = 120

# Counter to check if smth has been processed
global_labels_info_count = {}

processed_count = 0
merged_counter = 0
label_encoding_counter = 0

base_image_ref_dict = {}
skipped_dict = {"segmentation_files": [], "base_images": []}


# RTSTRUCT mask_5--1--Lung-Right-meta.json
# RTSTRUCT mask_5--1--Lung-Right.nii.gz
def get_seg_info(input_nifti):
    print(f"# Get seg configuration for: {basename(input_nifti)}")
    model_id = basename(input_nifti).replace(".nii.gz", "").split("--")[-1]
    seg_nifti_id = basename(input_nifti).replace(".nii.gz", "")
    print(f"# {model_id=}")
    print(f"# {seg_nifti_id=}")
    json_files_found = glob(join(dirname(input_nifti), "*.json"), recursive=False)
    json_files_found = [x for x in json_files_found if "model_combinations" not in x]
    assert len(json_files_found) > 0

    if any("-meta.json" in x for x in json_files_found):
        print("-meta.json identified ...")
        if len(json_files_found) == 1:
            assert "-meta.json" in json_files_found[0]
        else:
            print("No single meta-json found -> search for specific config...")
            model_id_search_string = f"--{model_id.lower()}-meta.json"
            print(f"Search for {model_id_search_string=}")
            json_files_found = [
                x for x in json_files_found if model_id_search_string in x.lower()
            ]
            print(json_files_found)
            assert len(json_files_found) == 1
        meta_info_json_path = json_files_found[0]

        seg_id = input_nifti.split("--")[-2]
        label_int = None
        label_name = None
        existing_configuration = {}
        with open(meta_info_json_path, "rb") as f:
            meta_info = json.load(f)

        if "segmentAttributes" in meta_info:
            for entries in meta_info["segmentAttributes"]:
                for part in entries:
                    if "labelID" in part and str(part["labelID"]) == seg_id:
                        label_int = int(part["labelID"])
                        if "SegmentLabel" in part:
                            label_name = part["SegmentLabel"]
                            break

                        elif "TrackingIdentifier" in part:
                            label_name = part["TrackingIdentifier"]
                            break

        assert label_name is not None
        assert label_int is not None

        existing_configuration[label_name] = str(label_int)

    elif any("seg_info" in x for x in json_files_found):
        print("seg_info identified ...")
        json_files_found = [
            meta_json_path
            for meta_json_path in json_files_found
            if f"seg_info-{model_id}.json" in meta_json_path
        ]
        assert len(json_files_found) == 1
        meta_info_json_path = json_files_found[0]
        existing_configuration = {}
        print(f"# Found nnunet meta-json: {meta_info_json_path}")
        with open(meta_info_json_path, "rb") as f:
            meta_info = json.load(f)

        if "seg_info" in meta_info:
            for label_entry in meta_info["seg_info"]:
                label_int = label_entry["label_int"]
                label_name = label_entry["label_name"]
                existing_configuration[label_name] = str(label_int)

    elif len(json_files_found) > 0:
        filtered_jsons = [
            meta_json_path
            for meta_json_path in json_files_found
            if seg_nifti_id in meta_json_path
        ]
        if len(filtered_jsons) == 1:
            existing_configuration = {}
            meta_info_json_path = filtered_jsons[0]
            print(f"# Found corrected nnunet meta-json: {meta_info_json_path}")
            with open(meta_info_json_path, "rb") as f:
                meta_info = json.load(f)

            if "seg_info" in meta_info:
                for label_entry in meta_info["seg_info"]:
                    label_int = label_entry["label_int"]
                    label_name = label_entry["label_name"]
                    existing_configuration[label_name] = str(label_int)
        else:
            print(
                f"# Found seg-ifo json files -> but could not identify an info-system!"
            )
            print(f"# NIFTI-file {input_nifti}")
    else:
        print(f"# Could not find seg-ifo json file!")
        print(f"# NIFTI-file {input_nifti}")
    return existing_configuration


def collect_labels(queue_list):
    global label_encoding_counter, global_labels_info

    label_encoding_counter = 0
    global_labels_info = {"Clear Label": 0}
    print(f"# Creating new gloabl labels info")

    found_label_keys = []
    for base_image_dict in queue_list:
        img_niftis = base_image_dict["seg_files"]
        for nifti in img_niftis:
            seg_configuration = get_seg_info(nifti)
            assert seg_configuration is not None
            for label_key, encoding_int in seg_configuration.items():
                if label_key not in found_label_keys:
                    found_label_keys.append(label_key)

    # python's sorted() function sorts the list found_label_keys by default in an ascending sort in alphabetic (lexicographic) order.
    found_label_keys = sorted(found_label_keys)
    print(f"# Found {len(found_label_keys)} labels -> generating global seg info...")

    for label_found in found_label_keys:
        if label_found.lower() == "Clear Label".lower():
            continue
        label_encoding_counter += 1
        assert label_encoding_counter not in global_labels_info.values()
        assert label_found not in global_labels_info
        # new globally valid label encodings get assigned to found_labels
        global_labels_info[label_found] = label_encoding_counter
    print("# Generated global_labels_info: ")
    print(json.dumps(global_labels_info, indent=4, sort_keys=True, default=str))
    write_global_seg_info(file_path=global_labels_info_path)


def write_global_seg_info(file_path):
    global global_labels_info
    print(f"# Writing global_labels_info -> {file_path} ")
    with open(file_path, "w", encoding="utf-8") as jsonData:
        json.dump(global_labels_info, jsonData, indent=4, ensure_ascii=True)


def read_global_seg_info():
    global global_labels_info_path, global_labels_info, label_encoding_counter

    print(f"# reading global_seg_info ...")
    if not exists(global_labels_info_path):
        print(f"# Global seg_info not present at {global_labels_info_path}! ")
        print("# -> Creating new file ...")
        global_labels_info = {"Clear Label": 0}
        write_global_seg_info(file_path=global_labels_info_path)

    with open(global_labels_info_path, "r") as f:
        global_labels_info = json.load(f)

    assert len(set(global_labels_info.values())) == len(global_labels_info)

    if label_encoding_counter == 0:
        label_encoding_counter = max(global_labels_info.values())
        print(f"# set label_encoding_counter to {label_encoding_counter}")


def check_transformations(current_config):
    global global_labels_info_count, global_labels_info, target_dict_dir, delete_non_target_labels, label_encoding_counter

    read_global_seg_info()
    transformations = {}
    for label_key, int_encoding in current_config.items():
        int_encoding = int(int_encoding)
        if label_key not in global_labels_info:
            if target_dict_dir is not None:
                print(
                    f"# Label {label_key} was found in current_config -> but not in target config!"
                )
                if delete_non_target_labels:
                    print(
                        f"# Needed tranformation: int_encoding {int_encoding} -> ✘ delete"
                    )
                    transformations[int_encoding] = {"kind": "delete"}
                else:
                    label_encoding_counter += 1
                    print(
                        f"# -> added label_int {label_encoding_counter} to global_labels_info"
                    )
                    assert label_encoding_counter not in global_labels_info.values()

                    global_labels_info[label_key] = label_encoding_counter
                    global_labels_info_count[label_key] = 1
                    write_global_seg_info(file_path=global_labels_info_path)
                    # existing_labels_with_encoding = list(global_labels_info.keys())[list(global_labels_info.values()).index(int_encoding)]
                    if label_encoding_counter == int_encoding:
                        print(f"# No transformation needed.")
                        print(f"#")
                    else:
                        print(
                            f"# New encoding needed: {int_encoding} -> switching to {label_encoding_counter}"
                        )
                        transformations[int_encoding] = {
                            "kind": "change",
                            "label_name": label_key,
                            "new_encoding": label_encoding_counter,
                        }
                        continue
            else:
                print(
                    f"# Label {label_key} was found in current_config -> but not in global_labels_info!"
                )
                label_encoding_counter += 1
                print(
                    f"# -> added label_int {label_encoding_counter} to global_labels_info"
                )
                global_labels_info[label_key] = label_encoding_counter
                global_labels_info_count[label_key] = 1
                write_global_seg_info(file_path=global_labels_info_path)
                # existing_labels_with_encoding = list(global_labels_info.keys())[list(global_labels_info.values()).index(int_encoding)]
                if label_encoding_counter == int_encoding:
                    print(f"# No transformation needed.")
                else:
                    print(
                        f"# New encoding needed: {int_encoding} -> switching to {label_encoding_counter}"
                    )
                    transformations[int_encoding] = {
                        "kind": "change",
                        "label_name": label_key,
                        "new_encoding": label_encoding_counter,
                    }
                    continue

        else:
            should_int_encoding = int(global_labels_info[label_key])
            if label_key not in global_labels_info_count:
                global_labels_info_count[label_key] = 1
            else:
                global_labels_info_count[label_key] += 1

            if int_encoding != should_int_encoding:
                print(f"# current: {label_key} : {int_encoding}")
                print(f"# target:  {label_key} : {should_int_encoding}")
                print(
                    f"# Needed tranformation: task_target {int_encoding} -> {should_int_encoding}"
                )
                transformations[int_encoding] = {
                    "kind": "change",
                    "label_name": label_key,
                    "new_encoding": should_int_encoding,
                }
                continue
            else:
                print(
                    f"# ✓ {label_key}: current {int_encoding} == global {should_int_encoding}"
                )

    return transformations


def create_metadata_json(new_labels_dict):
    if "Clear Label" not in new_labels_dict:
        new_labels_dict["Clear Label"] = 0

    metadata_dict = {"segmentAttributes": []}

    for label_key, int_encoding in new_labels_dict.items():
        metadata_dict["segmentAttributes"].append(
            [
                {
                    "SegmentLabel": str(label_key),
                    "TrackingIdentifier": str(label_key),
                    "labelID": int(int_encoding),
                }
            ]
        )

    return metadata_dict


class SparseToDenseProxy:
    def __init__(self, sparse_array: sparse.COO, dtype=np.int64):
        self.sparse = sparse_array
        self.shape = sparse_array.shape
        self.dtype = dtype

    def __getitem__(self, key):
        # Extract a slice from the sparse array and convert to dense
        return self.sparse[key].todense().astype(self.dtype)

    def __array__(self):
        # Only called if forced to a real NumPy array
        return self.sparse.todense().astype(self.dtype)


def load_sparse_nifti(proxy_array: nib.arrayproxy, dtype=int) -> sparse.COO:
    """
    Load a NIfTI image as a sparse COO array.
    :param proxy_array: NIfTI image proxy array
    :return: Sparse COO array representation of the NIfTI image
    """
    # Convert the proxy array to a numpy array
    coords = []
    data = []
    shape = proxy_array.shape
    logger.info(f"{shape=}")

    dense_image = proxy_array.get_fdata()

    sparse_image = sparse.COO.from_numpy(dense_image).astype(dtype)
    del dense_image
    return sparse_image

    if len(shape) == 3:
        for slice in range(shape[2]):
            slice_data = proxy_array.dataobj[:, :, slice]
            sparse_slice = sparse.COO.from_numpy(slice_data).astype(dtype)
            slice_dimension = np.full((1, sparse_slice.coords.shape[1]), slice)

            slice_coords = np.vstack([sparse_slice.coords, slice_dimension])

            coords.append(slice_coords)

            data.append(sparse_slice.data)

        coords = np.concatenate(coords, axis=1)
        data = np.concatenate(data, axis=0)

    logger.info(f"coords: {coords}")
    logger.info(f"coords.shape : {coords.shape}")
    logger.info(f"{data=}")

    return sparse.COO(coords=coords, data=data, shape=shape).astype(dtype)


def check_overlap(
    gt_map: sparse.COO, new_map: sparse.COO, seg_nifti
) -> Tuple[bool, np.ndarray, float]:
    """
    Return information about overlap between two segmentations.
    :param gt_map: ground truth map
    :param new_map: new map to check for overlap
    :param seg_nifti: segmentation nifti file name

    Return values:

    - result_overlap: True if overlap is found, False otherwise
    - overlap_indices: indices of the overlapping voxels
    - overlap_percentage: percentage of overlapping voxels
    """
    global skipped_dict, max_overlap_percentage

    # gt_map = np.where(gt_map != 0, 1, gt_map)
    gt_map = sparse.COO(gt_map.coords, 1, shape=gt_map.shape).astype(int)
    # new_map = np.where(new_map != 0, 1, new_map)
    new_map = sparse.COO(new_map.coords, 1, shape=gt_map.shape).astype(int)

    agg_arr = gt_map + new_map
    max_value = agg_arr.amax()  #  int(np.amax(agg_arr))
    if max_value > 1:
        print("# overlap Segmentations!!!")
        print(f"# NIFTI: {seg_nifti}")
        overlap_indices = agg_arr > 1
        overlap_voxel_count = overlap_indices.sum()
        overlap_percentage = 100 * float(overlap_voxel_count) / float(gt_map.size)

        print(f"# overlap_percentage: {overlap_percentage} / {max_overlap_percentage}")
        if overlap_percentage > max_overlap_percentage:
            print("# Too many voxels are overlap -> skipping")
            print(
                f"# overlap_percentage: {overlap_percentage:.6f} > max_overlap_percentage: {max_overlap_percentage}"
            )
            skipped_dict["segmentation_files"].append(
                f"-> removed: {basename(seg_nifti)}: {overlap_percentage:.6f}% / {max_overlap_percentage}% overlap"
            )
            return True, overlap_indices, overlap_percentage
        else:
            print("# Not enough voxels are overlap -> ok")
            skipped_dict["segmentation_files"].append(
                f"-> still ok: {basename(seg_nifti)}: {overlap_percentage:.6f}% / {max_overlap_percentage}% overlap"
            )
            return False, None, None
    else:
        return False, None, None


def merge_niftis(queue_dict):
    global merge_found_niftis, global_labels_info, global_labels_info_count, merged_counter, delete_merged_data, fail_if_overlap, skipping_level

    # load queue_dict entries to variables
    target_dir = queue_dict["target_dir"]
    base_image_path = queue_dict["base_image"]
    seg_nifti_list = queue_dict["seg_files"]
    multi = queue_dict["multi"]
    Path(target_dir).mkdir(parents=True, exist_ok=True)

    # start merging process by defining new_gt_map as shaped as base_image
    base_image_loaded = nib.load(base_image_path)
    base_image_dimensions = base_image_loaded.shape
    try:
        sparse_new_groundtruth_mapping = sparse.COO(
            coords=[], shape=base_image_dimensions
        ).astype(int)
        # new_gt_map = np.zeros_like(base_image_loaded.get_fdata().astype(int))
    except EOFError:
        return queue_dict, "false satori export"
    # new_gt_map_int_encodings = list(np.unique(new_gt_map))

    local_labels_info = {"Clear Label": 0}
    print(f"#### Processing images for base-image:")
    print(f"#### {base_image_path}")
    # iterate over corresponding seg_niftis of current base_image
    for seg_nifti in seg_nifti_list:
        seg_nifti_id = basename(seg_nifti).replace(".nii.gz", "")

        if not merge_found_niftis:
            print(f"# Resetting local_labels_info...")
            # new_gt_map = np.zeros_like(base_image_loaded.get_fdata().astype(int))
            sparse_new_groundtruth_mapping = sparse.COO(
                coords=[], shape=base_image_dimensions
            ).astype(int)
            local_labels_info = {"Clear Label": 0}
        print(f"# Processing NIFTI: {seg_nifti}")

        # get existing_configuration from meta_info: {"<label_name>": <label_int>}
        existing_configuration = get_seg_info(input_nifti=seg_nifti)

        if existing_configuration is None:
            return queue_dict, "label extraction issue"

        print("# -> got existing_configuration ...")
        print(f"# Loading NIFTI: {seg_nifti}")
        loaded_nib_nifti = nib.load(seg_nifti)

        # check dims of seg_nifti and resample if not fitting with base_image's dims
        if base_image_dimensions != loaded_nib_nifti.shape:
            print("# Issue with different dimensions in seg-NIFTIS!")
            print("# -> starting resampling..")
            resampling_success = resample_image(
                input_path=seg_nifti, original_path=base_image_path
            )
            if not resampling_success:
                return queue_dict, "resampling failed"
            print("# -> checking dimensions ...")
            loaded_nib_nifti = nib.load(seg_nifti)
            assert base_image_dimensions == loaded_nib_nifti.shape
            print("# -> dimensions ok")
        else:
            print("# No resampling needed.")

        #
        transformations = check_transformations(current_config=existing_configuration)
        if len(transformations) == 0:
            print(f"# No transformations needed!")
            print(f"# -> check if single file ...")
            if len(seg_nifti_list) == 1:
                print(f"# -> file ok")
                target_path = join(target_dir, basename(seg_nifti))
                if target_path != seg_nifti:
                    print(f"# -> copy file to target:{seg_nifti} -> {target_path}")
                    Path(dirname(target_path)).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src=seg_nifti, dst=target_path)

                # local_labels_info[label_name] = label_int
                metadata_json = create_metadata_json(new_labels_dict=global_labels_info)
                metadata_json_path = join(target_dir, f"{seg_nifti_id}.json")
                with open(metadata_json_path, "w", encoding="utf-8") as f:
                    json.dump(metadata_json, f, indent=4, sort_keys=False)
                return queue_dict, "ok"
            else:
                print("# -> merging multiple files -> continue")

        # loaded_seg_nifti_numpy = loaded_nib_nifti.get_fdata().astype(int)
        sparse_loaded_seg_nifti = load_sparse_nifti(loaded_nib_nifti)
        # nifti_int_encodings = list(np.unique(loaded_seg_nifti_numpy))
        nifti_int_encodings = list(np.unique(sparse_loaded_seg_nifti.data))
        if len(nifti_int_encodings) == 0:
            print("# No segmentation was found in result-NIFTI-file!")
            print(f"# NIFTI-file {seg_nifti}")
            continue

        for int_encoding in nifti_int_encodings:
            int_encoding = int(int_encoding)
            print(f"# Loading encoding {int_encoding}")
            if int_encoding == 0:
                continue

            # loaded_seg_nifti_label = np.where(
            #     loaded_seg_nifti_numpy != int_encoding, 0, loaded_seg_nifti_numpy
            # )
            array_by_int_encoding = sparse_loaded_seg_nifti == int_encoding
            loaded_seg_nifti_label = sparse.COO(
                coords=array_by_int_encoding.coords,
                data=int_encoding,
                shape=sparse_loaded_seg_nifti.shape,
            ).astype(int)
            label_found = list(existing_configuration.keys())[
                list(existing_configuration.values()).index(str(int_encoding))
            ]

            if len(transformations) > 0 and int_encoding in transformations:
                print(f"# label_bin: {int_encoding} -> transformation needed")
                transformation = transformations[int_encoding]
                kind = transformation["kind"]
                if kind == "change":
                    new_encoding = int(transformation["new_encoding"])
                    print(f"# change {label_found}: {int_encoding} -> {new_encoding}")
                    # loaded_seg_nifti_label = np.where(
                    #     loaded_seg_nifti_label == int_encoding,
                    #     new_encoding,
                    #     loaded_seg_nifti_label,
                    # )
                    loaded_seg_nifti_label = sparse.COO(
                        coords=array_by_int_encoding.coords,
                        data=new_encoding,
                        shape=array_by_int_encoding.shape,
                    ).astype(int)
                    int_encoding = new_encoding

                if kind == "delete":
                    print(f"# delete {label_found}: {int_encoding} -> 0")
                    # loaded_seg_nifti_label = np.where(loaded_seg_nifti_label == int_encoding, 0, loaded_seg_nifti_label)
                    continue

            if label_found not in local_labels_info:
                print(
                    f"# -> Adding label_found: {label_found}: {int_encoding} to local_labels_info"
                )
                local_labels_info[label_found] = int_encoding
            else:
                print(f"# Label already found in local_labels_info")
                print(f"# label_found: {label_found} - int_encoding: {int_encoding}")
                print(f"# vs")
                print(
                    f"# local_labels_info[{label_found}]: {local_labels_info[label_found]}"
                )
                assert local_labels_info[label_found] == int_encoding

            print("# Check overlap ...")
            result_overlap, overlap_indices, overlap_percentage = check_overlap(
                gt_map=sparse_new_groundtruth_mapping,
                new_map=loaded_seg_nifti_label,
                seg_nifti=seg_nifti,
            )
            if result_overlap:
                # existing_overlap_labels = np.unique(new_gt_map[overlap_indices])
                existing_overlap_labels = np.unique(
                    sparse_new_groundtruth_mapping[overlap_indices]
                )
                print(f"# Found overlap segmentation:")
                for existing_overlap_label_int in existing_overlap_labels:
                    existing_overlap_label = [
                        k
                        for k, v in global_labels_info.items()
                        if v == existing_overlap_label_int
                    ]
                    if len(existing_overlap_label) > 0:
                        existing_overlap_label = existing_overlap_label[0]
                    else:
                        print(
                            f"# Could not find any existing_overlap_label for encoding: {existing_overlap_label_int}"
                        )
                        existing_overlap_label = "Not found!"
                    print(f"# Base_image: {basename(base_image_path)}")
                    print(
                        f"# existing vs new: {existing_overlap_label} vs {label_found}"
                    )

                global_labels_info_count[label_found] -= 1
                if global_labels_info_count[label_found] <= 0:
                    del global_labels_info_count[label_found]
                    del global_labels_info[label_found]

                if not fail_if_overlap and skipping_level == "segmentation":
                    print(f"# Skipping this segmentation seg!")
                    continue
                else:
                    return queue_dict, "overlap"
            print("# -> no overlap ♥")
            print(f"# Merging new_gt_map + loaded_seg_nifti_label: {int_encoding}")
            # new_gt_map = np.maximum(new_gt_map, loaded_seg_nifti_label)
            sparse_new_groundtruth_mapping = np.maximum(
                sparse_new_groundtruth_mapping, loaded_seg_nifti_label
            )
        if not merge_found_niftis:
            print("# No NIFTI merge -> saving adusted NIFTI ...")
            target_nifti_path = join(target_dir, basename(seg_nifti))
            # combined = nib.Nifti1Image(
            #     new_gt_map, base_image_loaded.affine, base_image_loaded.header
            # )
            tmp_ground_truth_mapping = sparse_new_groundtruth_mapping.todense()
            combined = nib.Nifti1Image(
                tmp_ground_truth_mapping,
                base_image_loaded.affine,
                base_image_loaded.header,
            )
            combined.to_filename(target_nifti_path)
            del tmp_ground_truth_mapping
            metadata_json = create_metadata_json(new_labels_dict=local_labels_info)
            metadata_json_path = join(target_dir, f"{seg_nifti_id}.json")
            with open(metadata_json_path, "w", encoding="utf-8") as f:
                json.dump(metadata_json, f, indent=4, sort_keys=False)
            print(f"# JSON:  {metadata_json_path}")
            print(f"# NIFTI: {seg_nifti} -> {target_nifti_path}")

    if merge_found_niftis:
        print("# Writing new merged file...")
        # if int(np.amax(new_gt_map)) == 0:
        if int(sparse_new_groundtruth_mapping.amax()) == 0:
            print(f"#### No label found in new-label-map !")
            # return queue_dict, "no labels found"

        if multi:
            print(f"# Copy base image: {base_image_path}")
            target_dir = join(
                dirname(dirname(target_dir)),
                basename(base_image_path).replace(".nii.gz", "_merged"),
                basename(target_dir),
            )
            target_path_base_image = join(
                dirname(target_dir), "/".join(base_image_path.split("/")[-2:])
            )
            Path(dirname(target_path_base_image)).mkdir(parents=True, exist_ok=True)
            shutil.copy2(src=base_image_path, dst=target_path_base_image)

        Path(target_dir).mkdir(parents=True, exist_ok=True)
        merged_counter += 1
        metadata_json = create_metadata_json(local_labels_info)
        metadata_json_path = join(target_dir, "metadata.json")
        with open(metadata_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata_json, f, indent=4, sort_keys=False)
        target_path_merged = join(target_dir, f"{generate_uid()}_merged.nii.gz")
        # combined = nib.Nifti1Image(
        #     new_gt_map, base_image_loaded.affine, base_image_loaded.header
        # )
        tmp_ground_truth_mapping = sparse_new_groundtruth_mapping.todense()
        combined = nib.Nifti1Image(
            tmp_ground_truth_mapping,
            base_image_loaded.affine,
            base_image_loaded.header,
        )
        combined.to_filename(target_path_merged)
        del tmp_ground_truth_mapping
        print("# Checking if resampling is needed...")
        merged_nifti_shape = nib.load(target_path_merged).shape
        if base_image_dimensions != merged_nifti_shape:
            print(
                f"# Staring resampling: {base_image_dimensions} vs {merged_nifti_shape}"
            )
            resampling_success = resample_image(
                input_path=target_path_merged, original_path=base_image_path
            )
            if not resampling_success:
                return queue_dict, "resampling failed"
            print("# Check if resampling-result...")
            merged_nifti_shape = nib.load(target_path_merged).shape
            if base_image_dimensions != merged_nifti_shape:
                print("# ✘ Resampling was not successful!")
                return queue_dict, "resampling failed"
            else:
                print("# ✓  Resampling successful!")
        else:
            print("# No resampling needed.")

        if delete_merged_data:
            for seg_nifti in seg_nifti_list:
                print(f"# Removing merged NIFTI-file: {seg_nifti}")
                shutil.rmtree(seg_nifti, ignore_errors=True)

    print("# Done")
    return queue_dict, "ok"


def resample_image(input_path, original_path, replace=True, target_dir=None):
    global execution_timeout, executable, interpolator

    if not replace:
        if target_dir is None:
            print("# Replace == False and target_dir not set!")
            exit(1)
        target_path = join(target_dir, basename(input_path))
    else:
        target_path = input_path

    print(f"# Resampling: {input_path} -> {target_path}")
    command = [
        str(executable),
        "-t",
        str(original_path),
        "-i",
        str(input_path),
        "-o",
        str(target_path),
        "--interpolator",
        str(interpolator),
    ]
    output = run(
        command,
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True,
        timeout=execution_timeout,
    )
    # command stdout output -> output.stdout
    # command stderr output -> output.stderr
    if output.returncode != 0:
        print("##################  ERROR  #######################")
        print("# ----> Something went wrong with the shell-execution!")
        print(f"# Command:  {command}")
        print(f"# STDERR: {output.stderr}")
        return False

    assert exists(target_path)
    print(f"# -> OK")
    return True


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "batch")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

org_input_dir = getenv("ORG_IMG_IN_DIR", "None")
org_input_dir = org_input_dir if org_input_dir.lower() != "none" else None
assert org_input_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

executable = getenv("EXECUTABLE", "/kaapana/app/MitkCLResampleImageToReference.sh")
executable = executable if executable.lower() != "none" else None
assert executable is not None

#  Default: 2; allowed values: 1: Nearest Neighbour, 2: Linear, 3: BSpline 3, 4: WSinc Hamming, 5: WSinc Welch (optional), (default: 2), Type: Int
interpolator = getenv("INTERPOLATOR", "None")
interpolator = int(interpolator) if interpolator.lower() != "none" else 1

input_file_extension = getenv("INPUT_FILE_EXTENSION", "*.nii.gz")
input_file_extension = (
    input_file_extension if input_file_extension.lower() != "none" else None
)
assert input_file_extension is not None

parallel_processes = getenv("THREADS", "1")
parallel_processes = (
    int(parallel_processes) if parallel_processes.lower() != "none" else None
)
assert parallel_processes is not None

fail_if_overlap = getenv("FAIL_IF_OVERLAP", "None")
fail_if_overlap = True if fail_if_overlap.lower() == "true" else False

fail_if_label_already_present = getenv("FAIL_IF_LABEL_ALREADY_PRESENT", "None")
fail_if_label_already_present = (
    False if fail_if_label_already_present.lower() == "false" else True
)

fail_if_empty_gt = getenv("FAIL_IF_EMPTY_GT", "None")
fail_if_empty_gt = True if fail_if_empty_gt.lower() == "true" else False

fail_if_label_not_extractable = getenv("FAIL_IF_LABEL_ALREADY_PRESENT", "None")
fail_if_label_not_extractable = (
    False if fail_if_label_not_extractable.lower() == "false" else True
)

force_same_labels = getenv("FORCE_SAME_LABELS", "None")
force_same_labels = True if force_same_labels.lower() == "true" else False

delete_merged_data = getenv("DELETE_MERGED_DATA", "None")
delete_merged_data = False if delete_merged_data.lower() == "false" else True

merge_found_niftis = getenv("MERGE_FOUND_NIFTIS", "None")
merge_found_niftis = False if merge_found_niftis.lower() == "false" else True

target_dict_dir = getenv("TARGET_DICT_DIR", "None")
target_dict_dir = target_dict_dir if target_dict_dir.lower() != "none" else None

delete_non_target_labels = getenv("DELETE_NON_TARGET_LABELS", "None")
delete_non_target_labels = True if delete_non_target_labels.lower() == "true" else False

max_overlap_percentage = getenv("MAX_OVERLAP", "0.001")
max_overlap_percentage = (
    float(max_overlap_percentage) if max_overlap_percentage.lower() != "none" else None
)


skipping_level = "base_image"  # or 'segmentation'

print("# Starting resampling:")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# org_input_dir:    {org_input_dir}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print(f"# force_same_labels: {force_same_labels}")
print(f"# delete_merged_data: {delete_merged_data}")
print(f"# merge_found_niftis: {merge_found_niftis}")
print(f"# fail_if_overlap: {fail_if_overlap}")
print(f"# fail_if_label_already_present: {fail_if_label_already_present}")
print(f"# fail_if_label_not_extractable: {fail_if_label_not_extractable}")
print(f"# target_dict_dir: {target_dict_dir}")
print(f"# delete_non_target_labels: {delete_non_target_labels}")
print(f"# parallel_processes: {parallel_processes}")
print(f"# max_overlap_percentage: {max_overlap_percentage}")
print("# Starting processing on BATCH-ELEMENT-level ...")


global_labels_info_path = join(
    "/", workflow_dir, "global-seg-info", "global_seg_info.json"
)
Path(dirname(global_labels_info_path)).mkdir(parents=True, exist_ok=True)
print(f"# global_labels_info_path: {global_labels_info_path}")

if target_dict_dir is not None:
    read_global_seg_info()
    print("# Loaded global_labels_info: ")
    print(json.dumps(global_labels_info, indent=4, sort_keys=True, default=str))

batch_dir_path = join("/", workflow_dir, batch_name)

### COMPOSE base_image_ref_dict ###
# Loop for every batch-element (usually series)
batch_folders = sorted([f for f in glob(join(batch_dir_path, "*"))])
for batch_element_dir in batch_folders:

    print(f"# Processing batch-element {batch_element_dir}")

    element_output_dir = join(batch_element_dir, operator_out_dir)
    base_input_dir = join(batch_element_dir, org_input_dir)
    seg_input_dir = join(batch_element_dir, operator_in_dir)
    base_files = sorted(glob(join(base_input_dir, "*.nii*"), recursive=False))
    if len(base_files) != 1:
        print(
            f"# Something went wrong with DICOM to NIFTI conversion for series: {batch_element_dir}"
        )
        print(
            "# Probaly the DICOM is corrupted, which results in multiple volumes after the conversion."
        )
        print(
            "# You can manually remove this series from the tmp processing data and restart the SEG-Check operator."
        )
        print(f"# {base_files=}")
        print("# Abort")
        exit(1)

    seg_files = sorted(glob(join(seg_input_dir, "*.nii*"), recursive=False))
    if len(seg_files) == 0:
        print(f"# No segmentation NIFTI found -> skipping")
        continue

    base_file = base_files[0]
    base_series_id = basename(base_file)
    if base_series_id not in base_image_ref_dict:
        base_image_ref_dict[base_series_id] = {
            "base_file": base_file,
            "output_dir": element_output_dir,
            "batch_elements": {},
        }

    if batch_element_dir not in base_image_ref_dict[base_series_id]["batch_elements"]:
        base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir] = {
            "file_count": 0,
            "seg_files": [],
        }

    for seg_file in seg_files:
        if (
            seg_file
            not in base_image_ref_dict[base_series_id]["batch_elements"][
                batch_element_dir
            ]
        ):
            base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir][
                "seg_files"
            ].append(seg_file)
            base_image_ref_dict[base_series_id]["batch_elements"][batch_element_dir][
                "file_count"
            ] += 1

    batch_elements_sorted = {}
    for batch_element_dir in sorted(
        base_image_ref_dict[base_series_id]["batch_elements"],
        key=lambda batch_element_dir: base_image_ref_dict[base_series_id][
            "batch_elements"
        ][batch_element_dir]["file_count"],
        reverse=True,
    ):
        batch_elements_sorted[batch_element_dir] = base_image_ref_dict[base_series_id][
            "batch_elements"
        ][batch_element_dir]

    base_image_ref_dict[base_series_id]["batch_elements"] = batch_elements_sorted
### base_image_ref_dict composed and is strcutured as described in the following
# {
#   "<ct_nifti_fname>": {
#       "base_file": "<path_to_ct_nifti_fname>",
#       "output_dir": "<path_to_segcheck_out_dir>",
#       "batch_elements": {
#           "<path_of_batch_element>": {
#               "file_count": <number_of_segnifti_belonging_to_ctnifti>,
#               "seg_files": [
#                   <list_of_paths_to_segniftis>
#               ]
#           }
#       }
#   },
#   "<ct_nifti_fname>": {
#       ...
#   }
# }

### COMPOSE queue_dicts ###
queue_dicts = []
# iterate over ct_nifti_fname of base_image_ref_dict
for key in sorted(
    base_image_ref_dict.keys(),
    key=lambda key: base_image_ref_dict[key]["batch_elements"][
        list(base_image_ref_dict[key]["batch_elements"].keys())[0]
    ]["file_count"],
    reverse=True,
):
    value = base_image_ref_dict[key]
    base_image = value["base_file"]
    batch_elements_with_files = value["batch_elements"]

    multi = False
    target_dir = value["output_dir"]
    if len(batch_elements_with_files.keys()) == 1:
        pass
    elif len(batch_elements_with_files.keys()) > 1:
        multi = True
    else:
        print("# unknown list!")
        exit(1)

    segs_to_merge = {
        "base_image": base_image,
        "target_dir": target_dir,
        "multi": multi,
        "seg_files": [],
        "batch_elements_to_remove": [],
    }
    for batch_element_with_files, info_dict in batch_elements_with_files.items():
        if multi:
            segs_to_merge["batch_elements_to_remove"].append(batch_element_with_files)
        if not isinstance(info_dict["seg_files"][0].split("--")[-2], int):
            for seg_element_file in sorted(info_dict["seg_files"], reverse=False):
                segs_to_merge["seg_files"].append(seg_element_file)
        else:
            for seg_element_file in sorted(
                info_dict["seg_files"],
                key=lambda seg_element_file: (
                    seg_element_file.split("/")[-3],
                    int(seg_element_file.split("--")[-2]),
                ),
                reverse=False,
            ):
                segs_to_merge["seg_files"].append(seg_element_file)

        # for seg_element_file in info_dict["seg_files"]:
    queue_dicts.append(segs_to_merge)
### queue_dicts composed and is strcutured as described in the following
# [
#   {
#       "base_image": "<path_to_ct_nifti_fname>",
#       "target_dir": "<path_to_segcheck_out_dir>",
#       "multi": <indicator_whether_multiple_base_images_are_present>
#       "seg_files": [
#           <list_of_paths_to_segniftis>
#       ],
#       "batch_elements_to_remove": [
#           <list_of_paths_of_base_images_to_remove>
#       ],
#   }
# ]

#
if target_dict_dir is None:
    # collects labels from all present batch elements, sorts in alphabetic order and assigns new ascending label encodings
    # writes global_seg_info to global_seg_info.json:
    # {
    #     "Clear Label": 0,
    #     "aorta": 1,
    #     "esophagus": 2,
    #     "gallbladder": 3,
    #     ...,
    # }
    collect_labels(queue_list=queue_dicts)

print(f"# Starting {len(queue_dicts)} merging jobs ... ")
with ThreadPool(parallel_processes) as threadpool:
    nifti_results = threadpool.imap_unordered(merge_niftis, queue_dicts)
    for queue_dict, nifti_result in nifti_results:
        processed_count += 1
        target_dir = queue_dict["target_dir"]
        seg_nifti_list = queue_dict["seg_files"]
        base_image = queue_dict["base_image"]
        batch_elements_to_remove = queue_dict["batch_elements_to_remove"]

        remove_elements = False
        print(f"# Result for {base_image} arrived: {nifti_result}")
        print(f"# ----> process_count: {processed_count}/{len(queue_dicts)}")
        if nifti_result == "ok":
            remove_elements = True
        elif nifti_result == "overlap":
            if fail_if_overlap:
                exit(1)
            elif skipping_level == "base_image":
                print(
                    f"# Skipping overlap segmentations -> deleting batch-elements for gt-image: {base_image}"
                )
                skipped_dict["base_images"].append(base_image)
                remove_elements = True
            else:
                print(f"# Should not happen...")
                exit(1)

        elif nifti_result == "extracted_label_tag is None":
            if fail_if_label_not_extractable:
                exit(1)
        elif nifti_result == "seg_id is None":
            exit(1)
        elif nifti_result == "resampling failed":
            exit(1)
        elif nifti_result == "label extraction issue":
            exit(1)
        elif nifti_result == "no labels found":
            print("# No labels could be found in merged-gt-mask! ")
            print(f"# {base_image}")
            if fail_if_empty_gt:
                exit(1)
            else:
                remove_elements = True
                print("# Skipping -> deleting batch-elements for gt-image: ")
        elif nifti_result == "false satori export":
            remove_elements = True
            print("# Skipping -> deleting batch-elements for gt-image: ")
        else:
            print(f"# Unknown status message: {nifti_result}")
            exit(1)
        if remove_elements:
            for batch_element_to_remove in batch_elements_to_remove:
                print(f"# Removing merged dir: {batch_element_to_remove}")
                shutil.rmtree(batch_element_to_remove, ignore_errors=True)

if len(skipped_dict["base_images"]) > 0 or len(skipped_dict["segmentation_files"]) > 0:
    print("# Overlap elements: ")
    print(json.dumps(skipped_dict, indent=4, sort_keys=True, default=str))

if processed_count == 0:
    print("##################  ERROR  #######################")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    exit(1)
else:
    print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
    print("# DONE #")
