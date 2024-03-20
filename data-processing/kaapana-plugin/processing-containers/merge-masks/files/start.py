from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from logger_helper import get_logger
import logging
import json
import shutil
from glob import glob
from pathlib import Path
import shutil
import nibabel as nib
import numpy as np
import json
import re

processed_count = 0
skip_operator = False
issue_occurred = False
logger = None


def remove_special_characters(input_string):
    # Convert the string to lowercase
    input_string = input_string.lower()
    # Define the regex pattern
    pattern = re.compile("[^a-z0-9.]")
    # Use sub() method to replace matched characters with underscores
    result = re.sub(pattern, "", input_string)

    return result


def combine(
    seg_info_list, target_seg_info_dict, input_files, target_nifti_path, target_dir
):
    global processed_count, input_file_extension

    # define base_imgs for combining process
    base_img = None
    base_img_numpy = None
    base_img_labels = None

    # multiple labels in seg_info -> combine them
    for label_entry in seg_info_list:
        label_entry["file_found"] = False
        # label_name = label_entry["label_name"].lower().replace(" ", "").replace(",", "")
        label_name = remove_special_characters(label_entry["label_name"])
        label_int = label_entry["label_int"]

        # find fitting nifti file to current label, use {label_int}{label_name} for files with same label_name
        fitting_nifti_found = []
        for x in input_files:
            spec_removed = remove_special_characters(x)
            with_label_int = f"{label_int}{label_name}.nii.gz"
            wo_label_int = f"{label_name}.nii.gz"
            if with_label_int in spec_removed or wo_label_int in spec_removed:
                fitting_nifti_found.append(x)

        if len(fitting_nifti_found) != 1:
            logger.warning("")
            logger.warning("")
            logger.warning("")
            logger.warning(
                f"Segmentation {basename(label_name)} does not exist -> skipping ..."
            )
            logger.warning("")
            logger.warning("")
            logger.warning("")
            continue

        # confirm nifti file found and start combinig
        label_entry["file_found"] = True
        label_nifti_path = fitting_nifti_found[0]
        input_files.remove(label_nifti_path)
        logger.info("")
        logger.info("")
        logger.info(f"Combining {basename(label_nifti_path)}")

        # load current nifti and it's numpy array
        nifti_loaded = nib.load(label_nifti_path)
        nifti_numpy = nifti_loaded.get_fdata().astype(int)

        # modify one-hot encoded numpy array to have label_int as encoding integer in segmentation label mask
        nifti_numpy[nifti_numpy == 1] = label_int
        nifti_labels_found = list(np.unique(nifti_numpy))
        logger.info(f"New labels found {nifti_labels_found}")

        # if no one-hot encoded label was found in nifti numpy array --> skip segmentation label mask
        if len(nifti_labels_found) == 1:
            logger.warning("No annotation has been found -> skipping mask ...")
            continue

        # first of to-be-combined niftis serves as base image
        if base_img == None:
            base_img = nifti_loaded
            base_img_numpy = nifti_numpy
            base_img_labels = nifti_labels_found
            logger.info(f"Set base_img with labels: {base_img_labels}")
            processed_count += 1
            target_seg_info_dict["seg_info"].append(label_entry)
            continue

        # can not combine niftis with different shapes --> throw error
        if base_img.shape != nifti_loaded.shape:
            logger.error("")
            logger.error(basename(label_nifti_path))
            logger.error("Shape miss-match! -> Error")
            logger.error("")
            exit(1)

        # check whether label_int of current label was already combined with a previous nifti; if yes --> throw error
        duplicates_found = [
            x for x in nifti_labels_found if x != 0 and x in base_img_labels
        ]
        for duplicate in duplicates_found:
            logger.error("")
            logger.error(f"Label {duplicate} has already been found! -> Error")
            logger.error("")
        else:
            logger.info("No duplicates found.")
        if len(duplicates_found) > 0:
            exit(1)

        # check potential overlap of current segmentation label mask and already combined masks
        overlap_percentage = check_overlap(base_map=base_img_numpy, new_map=nifti_numpy)
        # if overlap, ignore current segmentation label mask in combining process
        if overlap_percentage > 0:
            logger.error("")
            logger.error(label_nifti_path)
            logger.error(
                f"Overlap ({overlap_percentage} %) has been identified! -> copy org nifti"
            )
            logger.error("")
            continue

        logger.info(" -> no overlap ♥")
        logger.info(" Combining base_img_numpy + nifti_numpy ...")
        logger.info("")
        # combine current nifti numpy array with already combined nifti stack
        # combining via taking from each pixel max value; as overlaps are already sorted out, it is always just label_int vs. 0
        base_img_numpy = np.maximum(base_img_numpy, nifti_numpy)
        base_img_labels = list(np.unique(base_img_numpy))
        target_seg_info_dict["seg_info"].append(label_entry)
        processed_count += 1

    # generate final nifti file from combined niftis
    logger.info(f" Generating combined result NIFTI @{basename(target_nifti_path)}")
    assert len(base_img_labels) > 1
    result_nifti = nib.Nifti1Image(base_img_numpy, base_img.affine, base_img.header)
    result_nifti.to_filename(target_nifti_path)
    logger.info(f"Done {processed_count=}")

    if len(input_files) > 0:
        left_over_path = join(target_dir, "left_over_niftis.txt")
        with open(left_over_path, "w") as f:
            for left_file in input_files:
                logger.warning("")
                logger.warning("#####################################################")
                logger.warning("")
                logger.warning(f" {basename(left_file)} has not been processed!")
                logger.warning("")
                logger.warning("#####################################################")
                logger.warning("")
                f.write(f"{basename(left_file)}\n")
        # exit(1)

    return True, target_seg_info_dict


def fuse(
    seg_info_list,
    target_seg_info_dict,
    meta_json_dict,
    input_files,
    target_nifti_path,
    target_dir,
):
    global processed_count, input_file_extension, skip_operator

    # get fusing-specific envs
    # first get the key specified in conf
    fuse_labels_key = getenv("FUSE_LABELS_KEY", "None")
    fuse_labels_key = fuse_labels_key if fuse_labels_key.lower() != "none" else None
    assert fuse_labels_key is not None
    # get the actual value
    fuse_labels = getenv(fuse_labels_key, "None")
    fuse_labels = fuse_labels if fuse_labels.lower() != "none" else None
    # assert fuse_labels is not None
    if fuse_labels is None:
        logger.warning("# WARNING")
        logger.warning("#")
        logger.warning("# NO FUSE_LABELS DEFINED. MARK OPERATOR AS SKIPPED")
        logger.warning("#")
        fuse_labels = ""
        skip_operator = True
        # exit(126)
    fuse_labels = fuse_labels.split(",")
    fuse_labels = [remove_special_characters(x) for x in fuse_labels]

    # first get the key specified in conf
    fused_label_name_key = getenv("FUSED_LABEL_NAME_KEY", "None")
    fused_label_name_key = (
        fused_label_name_key if fused_label_name_key.lower() != "none" else None
    )
    assert fused_label_name_key is not None
    # get the actual value
    fused_label_name = getenv(fused_label_name_key, "None")
    fused_label_name = fused_label_name if fused_label_name.lower() != "none" else None
    # assert fused_label_name is not None
    if fused_label_name is None:
        logger.warning("# WARNING")
        logger.warning("#")
        logger.warning("# NO FUSED_LABEL_NAMES DEFINED. MARK OPERATOR AS SKIPPED")
        logger.warning("#")
        fused_label_name = ""
        skip_operator = True
        # exit(126)
    fused_label_name = remove_special_characters(fused_label_name)

    logger.info("#")
    logger.info(f"# FUSING {fuse_labels} to {fused_label_name} !")
    logger.info("#")

    # gather information needed for fusion
    fusion_list = []
    for fuse_label in fuse_labels:
        # find fitting nifti file to current label
        fitting_nifti_found = [
            x
            for x in input_files
            if f"{fuse_label}.nii.gz" in remove_special_characters(x)
        ]

        # check whether fuse_label is in seg_info and get index
        fuse_label_index_in_seg_info = [
            index
            for index, item in enumerate(seg_info_list)
            if remove_special_characters(item["label_name"]) == fuse_label
        ]

        # check whether fuse_labels are in seg_info_list and input_files
        if len(fitting_nifti_found) == 0 or len(fuse_label_index_in_seg_info) == 0:
            logger.warning(
                f"Segmentation {fuse_label} does not exist -> fusion process aborted!"
            )
            break

        for i in range(0, len(fitting_nifti_found)):
            # compose a fuse_label_dict of current fuse_label
            fuse_label_dict = {}
            fuse_label_dict["label_name"] = fuse_label
            fuse_label_dict["label_int"] = seg_info_list[
                fuse_label_index_in_seg_info[i]
            ]["label_int"]
            fuse_label_dict["nifti_fname"] = fitting_nifti_found[i]
            nifti_loaded = nib.load(fuse_label_dict["nifti_fname"])
            fuse_label_dict["nifti_np_array"] = nifti_loaded.get_fdata().astype(int)

            # add fuse_label_dict to fusion_list
            fusion_list.append(fuse_label_dict)

        processed_count += 1

    if len(fusion_list) > 0:
        # get new label_int of fused labels, i.e. smallest label_int of fused labels
        fused_label_int = min(fusion_list, key=lambda x: x["label_int"])["label_int"]

        # check dims of fused label masks
        nifti_np_arrays = [item["nifti_np_array"] for item in fusion_list]
        dimensions_are_same = all(
            arr.shape == nifti_np_arrays[0].shape for arr in nifti_np_arrays
        )
        assert dimensions_are_same

        # fuse them to single nifti file and set all non-zero label_ints to fused_label_int
        fused_nifti_np = np.sum(nifti_np_arrays, axis=0)
        fused_nifti_np[fused_nifti_np != 0] = fused_label_int

        # save fused_nifti as nii.gz file
        result_nifti_fname = (
            dirname(target_nifti_path)
            + "/"
            + basename(input_files[0]).split("--")[0]
            + "--"
            + str(fused_label_int)
            + "--"
            + fused_label_name
            + ".nii.gz"
        )
        result_nifti = nib.Nifti1Image(
            fused_nifti_np, nifti_loaded.affine, nifti_loaded.header
        )
        result_nifti.to_filename(result_nifti_fname)

    # adapt seg_info JSON
    # add non-fuse labels
    target_seg_info_dict = [
        entry
        for entry in seg_info_list
        if remove_special_characters(entry["label_name"]) not in fuse_labels
    ]
    # add fused label
    if len(fusion_list) > 0:
        target_seg_info_dict.append(
            {"label_name": fused_label_name, "label_int": fused_label_int}
        )

    # adapt meta_json_dict JSON
    mod_segmentAttributes = []
    added_fused_label = False
    for segment in meta_json_dict["segmentAttributes"]:
        segment_label = remove_special_characters(segment[0]["SegmentLabel"])
        if segment_label in fuse_labels:
            if added_fused_label is False:
                # add fused label to mod_segmentAttributes
                mod_segment = json.loads(
                    json.dumps(segment[0]).replace(
                        segment[0]["SegmentLabel"], fused_label_name
                    )
                )
                mod_segment["labelID"] = fused_label_int
                # ensure that 'CodeMeaning' attribute is the same as 'SegmentLabel'
                if (
                    "SegmentedPropertyCategoryCodeSequence" in mod_segment
                    and "SegmentedPropertyTypeCodeSequence" in mod_segment
                ):
                    if (
                        "CodeMeaning"
                        in mod_segment["SegmentedPropertyCategoryCodeSequence"]
                        and "CodeMeaning"
                        in mod_segment["SegmentedPropertyTypeCodeSequence"]
                    ):
                        mod_segment["SegmentedPropertyCategoryCodeSequence"][
                            "CodeMeaning"
                        ] = mod_segment["SegmentLabel"]
                        mod_segment["SegmentedPropertyTypeCodeSequence"][
                            "CodeMeaning"
                        ] = mod_segment["SegmentLabel"]
                mod_segmentAttributes.append([mod_segment])
                added_fused_label = True
            else:
                continue
        else:
            mod_segmentAttributes.append(segment)
    meta_json_dict["segmentAttributes"] = mod_segmentAttributes

    # remove eventually present "\\t", "\t", "\\s", "\s", "\\n" or "\n"
    meta_json_dict = json.loads(
        json.dumps(meta_json_dict)
        .replace("\\t", "")
        .replace("\t", "")
        .replace("\\s", "")
        .replace("\s", "")
        .replace("\\n", "")
        .replace("\n", "")
    )

    # write meta_json_dict to output_dir
    meta_json_in_dir = glob(
        join(Path(dirname(input_files[0])), "*.json"), recursive=True
    )[0]
    meta_json_out_dir = meta_json_in_dir.replace(
        getenv("OPERATOR_IN_DIR"), getenv("OPERATOR_OUT_DIR")
    )
    with open(meta_json_out_dir, "w") as fp:
        json.dump(meta_json_dict, fp, indent=4)

    # copy non-fusde nifti files to output dir
    fusion_nifti_fnames = [entry["nifti_fname"] for entry in fusion_list]
    unmodified_nifti_fnames = [
        fname for fname in input_files if fname not in fusion_nifti_fnames
    ]
    for unmod_nifti_fname in unmodified_nifti_fnames:
        el_out_dir = unmod_nifti_fname.replace(
            getenv("OPERATOR_IN_DIR"), getenv("OPERATOR_OUT_DIR")
        )
        shutil.copyfile(unmod_nifti_fname, el_out_dir)

    logger.info(f"Done {processed_count=}")

    return True, target_seg_info_dict


def merge_mask_niftis(nifti_dir, target_dir, mode=None):
    global processed_count, input_file_extension, skip_operator

    Path(target_dir).mkdir(parents=True, exist_ok=True)

    json_files = glob(join(nifti_dir, "*.json"), recursive=True)
    seg_info_json = [x for x in json_files if "seg_info" in x]
    meta_info_json = [x for x in json_files if "-meta.json" in x]

    if len(seg_info_json) == 1:
        with open(seg_info_json[0], "r") as f:
            # get seg_info_dict in style {"seg_info": [{...}, {...}, {...}]}
            seg_info_dict = json.load(f)
    elif len(meta_info_json) == 1:
        with open(meta_info_json[0], "r") as f:
            meta_json_dict = json.load(f)
        assert "segmentAttributes" in meta_json_dict
        seg_info_dict = {"seg_info": []}
        for segment in meta_json_dict["segmentAttributes"]:
            seg_info_dict["seg_info"].append(
                {
                    "label_name": segment[0]["SegmentLabel"],
                    "label_int": segment[0]["labelID"],
                }
            )
    else:
        logger.info(f"No valid metadata json found @{nifti_dir}")
        exit(1)
    # ensure seg_info_list's desired form: [{...}, {...}, {...}]
    if isinstance(seg_info_dict, dict):
        if "seg_info" in seg_info_dict:
            seg_info_list = seg_info_dict["seg_info"]
    else:
        seg_info_list = seg_info_dict

    # define variables for combing or fusing
    target_nifti_path = join(target_dir, "combined_masks.nii.gz")
    target_seg_info_dict = {"seg_info": []}
    logger.info("seg_info loaded:")
    logger.info(json.dumps(seg_info_list, indent=4))

    # get nifti file names
    nifti_search_query = join(nifti_dir, "*.nii.gz")
    logger.info(f"Collecting NIFTIs @{nifti_search_query}")
    input_files = glob(nifti_search_query, recursive=False)
    logger.info(
        f"Found {len(input_files)} NIFTI files vs {len(seg_info_list)} seg infos ..."
    )
    assert len(input_files) > 0

    if mode == "combine":
        res, target_seg_info_dict = combine(
            seg_info_list,
            target_seg_info_dict,
            input_files,
            target_nifti_path,
            target_dir,
        )
    elif mode == "fuse":
        res, target_seg_info_dict = fuse(
            seg_info_list,
            target_seg_info_dict,
            meta_json_dict,
            input_files,
            target_nifti_path,
            target_dir,
        )
    else:
        # given mode is not supported --> through error
        logger.error(f"#")
        logger.error(
            f"# MODE not supported! Choose either mode 'combine' or 'fuse' segmentation label masks!"
        )
        logger.error(f"#")
        exit(1)

    return res, nifti_dir, target_seg_info_dict


def check_overlap(base_map, new_map):
    overlap_percentage = 0

    base_map = np.where(base_map != 0, 1, base_map)
    new_map = np.where(new_map != 0, 1, new_map)

    agg_arr = base_map + new_map
    max_value = int(np.amax(agg_arr))
    if max_value > 1:
        overlap_indices = agg_arr > 1
        overlap_voxel_count = overlap_indices.sum()
        overlap_percentage = 100 * float(overlap_voxel_count) / float(base_map.size)

    return overlap_percentage


if __name__ == "__main__":
    log_level = getenv("LOG_LEVEL", "info").lower()
    log_level_int = None
    if log_level == "debug":
        log_level_int = logging.DEBUG
    elif log_level == "info":
        log_level_int = logging.INFO
    elif log_level == "warning":
        log_level_int = logging.WARNING
    elif log_level == "critical":
        log_level_int = logging.CRITICAL
    elif log_level == "error":
        log_level_int = logging.ERROR

    logger = get_logger(__name__, log_level_int)

    workflow_dir = getenv("WORKFLOW_DIR", "None")
    workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
    assert workflow_dir is not None

    batch_name = getenv("BATCH_NAME", "None")
    batch_name = batch_name if batch_name.lower() != "none" else None
    assert batch_name is not None

    operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
    operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
    assert operator_in_dir is not None

    operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
    operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
    assert operator_out_dir is not None

    mode = getenv("MODE", "None")
    mode = mode if mode.lower() != "none" else None
    assert mode is not None

    logger.info("##################################################")
    logger.info("#")
    logger.info("# Starting merge-masks operator:")
    logger.info("#")
    logger.info(f"# workflow_dir:     {workflow_dir}")
    logger.info(f"# batch_name:       {batch_name}")
    logger.info(f"# operator_in_dir:  {operator_in_dir}")
    logger.info(f"# operator_out_dir: {operator_out_dir}")
    logger.info(f"# mode: {mode}")
    logger.info("#")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")
    logger.info("# Starting processing on BATCH-ELEMENT-level ...")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")

    # Loop for every batch-element (usually series)
    batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
    for batch_element_dir in batch_folders:
        logger.info("#")
        logger.info(f"# Processing batch-element {batch_element_dir}")
        logger.info("#")
        element_input_dir = join(batch_element_dir, operator_in_dir)
        element_output_dir = join(batch_element_dir, operator_out_dir)

        # check if input dir present
        if not exists(element_input_dir):
            logger.info("#")
            logger.info(f"# Input-dir: {element_input_dir} does not exists!")
            logger.info("# -> skipping")
            logger.info("#")
            continue
        else:
            # merge masks with mode
            success, nifti_dir, target_seg_info_dict = merge_mask_niftis(
                nifti_dir=element_input_dir,
                target_dir=element_output_dir,
                mode=mode,
            )

            target_seg_info_path = join(element_output_dir, "seg_info.json")
            assert not exists(target_seg_info_path)
            with open(target_seg_info_path, "w") as fp:
                json.dump(target_seg_info_dict, fp, indent=4)

    logger.info("#")
    logger.info("##################################################")
    logger.info("#")
    logger.info("# BATCH-ELEMENT-level processing done.")
    logger.info("#")
    logger.info("##################################################")
    logger.info("#")

    if processed_count == 0:
        logger.info("##################################################")
        logger.info("#")
        logger.info("# -> No files have been processed so far!")
        logger.info("#")
        logger.info("# Starting processing on BATCH-LEVEL ...")
        logger.info("#")
        logger.info("##################################################")
        logger.info("#")

        batch_input_dir = join("/", workflow_dir, operator_in_dir)
        batch_output_dir = join("/", workflow_dir, operator_in_dir)

        # check if input dir present
        if not exists(batch_input_dir):
            logger.info("#")
            logger.info(f"# Input-dir: {batch_input_dir} does not exists!")
            logger.info("# -> skipping")
            logger.info("#")
        else:
            # merge masks with mode
            success, nifti_dir, target_seg_info_dict = merge_mask_niftis(
                nifti_dir=batch_input_dir, target_dir=batch_output_dir, mode=mode
            )

            target_seg_info_path = join(batch_output_dir, "seg_info.json")
            assert not exists(target_seg_info_path)
            with open(target_seg_info_path, "w") as fp:
                json.dump(target_seg_info_dict, fp, indent=4)

        logger.info("#")
        logger.info("##################################################")
        logger.info("#")
        logger.info("# BATCH-LEVEL-level processing done.")
        logger.info("#")
        logger.info("##################################################")
        logger.info("#")

    if mode == "fuse" and skip_operator:
        logger.warning("#####################################")
        logger.warning("#")
        logger.warning("# NO FUSE LABELS SPECIFIED --> MARK OPERATOR AS SKIPPED!")
        logger.warning("#")
        logger.warning("#####################################")
        exit(126)

    if processed_count == 0:
        logger.info("#")
        logger.info("##################################################")
        logger.info("#")
        logger.info("##################  ERROR  #######################")
        logger.info("#")
        logger.info("# ----> NO FILES HAVE BEEN PROCESSED!")
        logger.info("#")
        logger.info("##################################################")
        logger.info("#")
        if issue_occurred:
            logger.info("#")
            logger.info("##################################################")
            logger.info("#")
            logger.info("# There were some issues!")
            logger.info("#")
            logger.info("##################################################")
            logger.info("#")
        exit(1)
    else:
        logger.info("#")
        logger.info(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
        logger.info("#")
        logger.info("# DONE #")
