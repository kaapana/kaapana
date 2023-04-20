from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from logger_helper import get_logger
from pathlib import Path
from PIL import Image
import numpy as np
import os
from rt_utils import RTStructBuilder
import matplotlib.pyplot as plt
from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
from pathlib import Path
from logger_helper import get_logger
import logging
from glob import glob
from pathlib import Path
from PIL import Image
import numpy as np
import re
import shutil
from subprocess import PIPE, run
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
from multiprocessing.pool import ThreadPool
import psutil

logger = None
processed_count = 0
execution_timeout = 10


def print_mem_usage(msg=""):
    logger.info(
        f"{msg}: Memory usage: {round(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)} MB"
    )
    logger.info("")


def dicomlab2LAB(dicomlab):
    lab = [
        (dicomlab[0] * 100.0) / 65535.0,
        (dicomlab[1] * 255.0) / 65535.0 - 128,
        (dicomlab[2] * 255.0) / 65535.0 - 128,
    ]
    return lab


def load_img(img_path, rgba=True):
    img_array = Image.open(img_path)
    if rgba:
        img_array = img_array.convert("RGBA")
    return np.array(img_array)


def create_thumbnail(parameters):
    global processed_count

    dcm_seg_dir, dcm_dir, target_dir = parameters
    base_image_slices_search_query = join(dcm_dir, "*.dcm")
    logger.info(f"Collecting base DICOMs from @{base_image_slices_search_query}")
    base_input_files = sorted(glob(base_image_slices_search_query, recursive=False))
    logger.info(f"Found {len(base_input_files)} base image input files ...")

    seg_search_query = join(dcm_seg_dir, "*.dcm")
    logger.info(f"Collecting SEG DICOMs from @{seg_search_query}")
    seg_input_files = glob(seg_search_query, recursive=False)
    logger.info(f"Found {len(seg_input_files)} seg image input files ...")

    assert len(seg_input_files) == 1
    assert len(base_input_files) > 1

    base_slice_count = len(base_input_files)

    seg_dcm = seg_input_files[0]
    modality_cmd = f"dcmdump {seg_dcm} --prepend --load-short --search 0008,0060"
    modality = (
        execute_command(cmd=modality_cmd, timeout=2)
        .stdout.split("\n")[0]
        .split(" ")[2]
        .replace("[", "")
        .replace("]", "")
    )
    seg_series_uid_cmd = f"dcmdump {seg_dcm} --prepend --load-short --search 0020,000E"
    seg_series_uid = (
        execute_command(cmd=seg_series_uid_cmd, timeout=2)
        .stdout.split("\n")[0]
        .split(" ")[2]
        .replace("[", "")
        .replace("]", "")
    )
    logger.info("Scanning base images ...!")
    print_mem_usage()

    scan_direction = None
    base_series_uids = {}
    for index, base_dcm in enumerate(base_input_files):
        if scan_direction is None:
            scan_dir_cmd = f"dcmdump {base_dcm} --search 0018,5100"
            scan_direction = execute_command(cmd=scan_dir_cmd, timeout=3)
            scan_direction = (
                scan_direction.stdout.replace("  ", "").replace("#", "")
                .split(" ")[2]
                .replace("[", "")
                .replace("]", "")
            )

        object_uid_cmd = f"dcmdump {base_dcm} --search 0008,0018"
        object_uid = execute_command(cmd=object_uid_cmd, timeout=3)
        object_uid = (
            object_uid.stdout.replace("  ", "")
            .split(" ")[2]
            .replace("[", "")
            .replace("]", "")
        )
        object_uid_cmd = f"dcmdump {base_dcm} --search 0008,0018"
        object_uid = execute_command(cmd=object_uid_cmd, timeout=3)
        object_uid = (
            object_uid.stdout.replace("  ", "")
            .split(" ")[2]
            .replace("[", "")
            .replace("]", "")
        )
        slice_index_cmd = f"dcmdump {base_dcm} --search 0020,0013"
        slice_index = execute_command(cmd=slice_index_cmd, timeout=3)
        slice_index = int(
            slice_index.stdout.split(" ")[2].replace("[", "").replace("]", "")
        )
        if scan_direction[0].lower() == "f":
            slice_index = base_slice_count - slice_index

        base_series_uids[object_uid] = {
            "slice_index": slice_index,
            "base_dcm": base_dcm,
            "seg_bmps": [],
        }

    base_series_uids = {
        k: v
        for k, v in sorted(
            base_series_uids.items(), key=lambda item: item[1]["slice_index"]
        )
    }
    if modality == "RTSTRUCT":
        logger.info("modality == RTSTRUCT")
        result = create_rtstruct_thumbnail(
            seg_dcm, dcm_dir, base_series_uids, target_dir, seg_series_uid
        )

    elif modality == "SEG":
        logger.info("modality == SEG")
        print_mem_usage()
        result = create_seg_thumbnail(
            seg_dcm, base_series_uids, target_dir, seg_series_uid
        )

    else:
        exit(1)

    if not result:
        logger.error("Something went wrong!")
        print_mem_usage()
        exit(1)
    else:
        processed_count += 1
        return True, dcm_seg_dir


def create_rtstruct_thumbnail(
    seg_dcm, dcm_dir, base_series_uids, target_dir, seg_series_uid
):
    logger.info("Searching for color definitions ...")
    cont_colors_cmd = (
        f"dcmdump {seg_dcm} --prepend --load-short +U8 --print-all --search 3006,002a"
    )
    cont_colors = execute_command(cmd=cont_colors_cmd, timeout=10).stdout.split("\n")
    cont_colors = [
        x.split(" ")[2].replace("]", "").replace("[", "").split("\\")
        for x in cont_colors
        if x != ""
    ]
    cont_colors = [[int(y) for y in x] for x in cont_colors]

    logger.info("Reading RTSTRUCT ...")
    try:
        rtstruct = RTStructBuilder.create_from(
            dicom_series_path=dcm_dir, rt_struct_path=seg_dcm
        )
    except:
        logger.info("Something went wrong!")
        exit(1)

    logger.info("Getting masks ...")
    print_mem_usage()
    seg_overlay = None
    slice_concat_reshape = None
    for index, roi_name in enumerate(rtstruct.get_roi_names()):
        logger.info(f"Processing: {roi_name} ...")
        try:
            mask_3d = rtstruct.get_roi_mask_by_name(roi_name)
        except Exception as e:
            logger.error("")
            logger.error("")
            logger.error("")
            logger.error(
                f"Something went wrong loading the label: {roi_name} -> skipping "
            )
            logger.error("")
            logger.error(f"Error: {e}")
            logger.error("")
            logger.error("")
            continue

        if seg_overlay is None:
            seg_overlay = np.zeros(
                (mask_3d.shape[0], mask_3d.shape[1], mask_3d.shape[2], 4)
            )

        color = cont_colors[index]
        slice_count = mask_3d.shape[2]
        slice_segs = mask_3d.reshape(
            mask_3d.shape[0] * mask_3d.shape[1], slice_count
        ).sum(axis=0)
        if slice_concat_reshape is None:
            slice_concat_reshape = slice_segs
        else:
            slice_concat_reshape = np.add(slice_concat_reshape, slice_segs)

        seg_overlay[:, :, :, 0][mask_3d > 0] = color[0]
        seg_overlay[:, :, :, 1][mask_3d > 0] = color[1]
        seg_overlay[:, :, :, 2][mask_3d > 0] = color[2]
        seg_overlay[:, :, :, 3][mask_3d > 0] = 200
        print_mem_usage()

    slice_segs = None
    slice_count = None
    mask_3d = None
    rtstruct = None

    correct_slice_id = int(np.argmax(slice_concat_reshape))
    slice_concat_reshape = None
    logger.info(f"Best slice identified: {correct_slice_id}")

    base_dcm_path = None
    for key, base_slice in base_series_uids.items():
        if base_slice["slice_index"] == correct_slice_id:
            base_dcm_path = base_slice["base_dcm"]
            break

    assert base_dcm_path is not None
    logger.info("Generating overlay ...")
    seg_overlay_slice = seg_overlay[:, :, correct_slice_id, :].astype("uint8")
    seg_overlay = None

    print_mem_usage()
    base_tmp_output_dir = join(target_dir, "tmp/base")
    shutil.rmtree(base_tmp_output_dir, ignore_errors=True)
    Path(base_tmp_output_dir).mkdir(parents=True, exist_ok=True)
    base_image_bmp_cmd = (
        f"dcm2pnm {base_dcm_path} --write-bmp +Wm {base_tmp_output_dir}/base.bmp"
    )
    output_result = execute_command(cmd=base_image_bmp_cmd, timeout=20)
    base_bmps = glob(join(base_tmp_output_dir, "*.bmp"), recursive=False)
    assert len(base_bmps) == 1

    target_png = join(target_dir, f"{seg_series_uid}.png")
    base_img_np = load_img(img_path=base_bmps[0], rgba=True)
    im = Image.fromarray(base_img_np)

    logger.info("Generating final thumbnail ...")
    print_mem_usage()
    im_overlay = Image.fromarray(seg_overlay_slice)
    final_image = Image.alpha_composite(im, im_overlay)
    final_image = final_image.resize(
        (thumbnail_size, thumbnail_size), resample=Image.BICUBIC
    )
    final_image.save(target_png)
    shutil.rmtree(base_tmp_output_dir, ignore_errors=True)

    return True


def create_seg_thumbnail(seg_dcm, base_series_uids, target_dir, seg_series_uid):
    logger.info("in create_seg_thumbnail")
    print_mem_usage()
    seg_ref_image_info_cmd = (
        f"dcmdump {seg_dcm} --prepend --load-short --search 0008,1155"
    )
    logger.info("Get seg_ref_img_info ...")
    print_mem_usage()
    seg_ref_img_info = execute_command(cmd=seg_ref_image_info_cmd, timeout=10)
    seg_ref_img_info = seg_ref_img_info.stdout.split("\n")

    seg_tmp_output_dir = join(target_dir, "tmp/seg")
    shutil.rmtree(seg_tmp_output_dir, ignore_errors=True)
    Path(seg_tmp_output_dir).mkdir(parents=True, exist_ok=True)

    seg_image_info_cmd = f"dcmdump {seg_dcm} --prepend --load-short --search 0020,9157"
    logger.info("Get seg_img_info ...")
    print_mem_usage()
    seg_img_info = execute_command(cmd=seg_image_info_cmd, timeout=10)
    seg_img_info = seg_img_info.stdout.split("\n")
    test = [x for x in seg_img_info if "(5200,9230)" not in x]
    seg_img_info = [x for x in seg_img_info if "(5200,9230)" in x and x != ""]

    seg_ref_image_info_cmd = (
        f"dcmdump {seg_dcm} --prepend --load-short --search 0008,1155"
    )
    logger.info("Get seg_ref_img_info ...")
    print_mem_usage()
    seg_ref_img_info = execute_command(cmd=seg_ref_image_info_cmd, timeout=10)
    seg_ref_img_info = seg_ref_img_info.stdout.split("\n")
    seg_ref_img_info = [x for x in seg_ref_img_info if "(5200,9230)" in x and x != ""]

    dicomlab_color_image_info_cmd = (
        f"dcmdump {seg_dcm} --prepend --load-short +U8 --print-all --search 0062,000d"
    )
    logger.info("Get dicomlab_color_img_info ...")
    print_mem_usage()
    dicomlab_color_img_info = execute_command(
        cmd=dicomlab_color_image_info_cmd, timeout=10
    )
    dicomlab_color_img_info = dicomlab_color_img_info.stdout.split("\n")
    dicomlab_color_img_info = [x for x in dicomlab_color_img_info if x != ""]

    seg_image_bmp_cmd = (
        f"dcm2pnm {seg_dcm} --write-bmp --all-frames {seg_tmp_output_dir}/seg"
    )
    logger.info("Generate seg_bmps ...")
    print_mem_usage()
    output_result = execute_command(cmd=seg_image_bmp_cmd, timeout=20)
    seg_bmps = sorted(glob(join(seg_tmp_output_dir, "*.bmp"), recursive=False))
    seg_bmps.sort(key=lambda f: int(re.sub("\D", "", f)))

    logger.info(f"len(seg_bmps):           {len(seg_bmps)}")
    logger.info(f"len(seg_img_info):       {len(seg_img_info)}")
    logger.info(f"len(seg_ref_img_info):   {len(seg_ref_img_info)}")
    logger.info(f"len(dicomlab_color_img_info): {len(dicomlab_color_img_info)}")

    assert len(seg_bmps) == len(seg_img_info) == len(seg_ref_img_info)

    logger.info("Collect seg thumbnails ...")
    print_mem_usage()
    for index, info in enumerate(seg_img_info):
        if info == "":
            continue
        info = info.split(" ")[2].replace("#", "").split("\\")
        seg_id = int(info[0]) - 1
        dicomlab = dicomlab_color_img_info[seg_id].split(" ")[2].split("\\")
        dicomlab = [float(int(x)) for x in dicomlab]
        color_rgb = dicomlab2LAB(dicomlab=dicomlab)
        lab = LabColor(color_rgb[0], color_rgb[1], color_rgb[2])
        color_rgb = convert_color(lab, sRGBColor).get_upscaled_value_tuple()
        color_rgb = [max(min(x, 255), 0) for x in color_rgb]
        slice_ref = (
            seg_ref_img_info[index].split(" ")[2].replace("[", "").replace("]", "")
        )
        assert slice_ref in base_series_uids
        base_series_uids[slice_ref]["seg_bmps"].append(
            {"bmp_file": seg_bmps[index], "colors": color_rgb}
        )

    logger.info("Identify best thumbnail slice ...")
    print_mem_usage()
    slice_max_segs = 0
    slice_max_id = None
    for index, base_slice in enumerate(base_series_uids):
        base_slice_element = base_series_uids[base_slice]
        if len(base_slice_element["seg_bmps"]) > slice_max_segs:
            slice_max_id = base_slice
            slice_max_segs = len(base_slice_element["seg_bmps"])

    correct_slice = base_series_uids[slice_max_id]
    logger.info(f"Best slice: {correct_slice}")

    base_tmp_output_dir = join(target_dir, "tmp/base")
    shutil.rmtree(base_tmp_output_dir, ignore_errors=True)
    Path(base_tmp_output_dir).mkdir(parents=True, exist_ok=True)
    base_image_bmp_cmd = f"dcm2pnm {correct_slice['base_dcm']} --write-bmp +Wm {base_tmp_output_dir}/base.bmp"
    output_result = execute_command(cmd=base_image_bmp_cmd, timeout=20)
    base_bmps = glob(join(base_tmp_output_dir, "*.bmp"), recursive=False)
    logger.info(f"Found {len(base_bmps)} base bmps ...")
    assert len(base_bmps) == 1

    logger.info("Generating overlay ...")
    print_mem_usage()
    base_img_np = load_img(img_path=base_bmps[0])
    seg_overlay = np.zeros_like(base_img_np)
    for index, seg_bmp in enumerate(correct_slice["seg_bmps"]):
        seg_img_np = load_img(img_path=seg_bmp["bmp_file"], rgba=False)
        seg_overlay[:, :, 0][seg_img_np > 0] = seg_bmp["colors"][0]
        seg_overlay[:, :, 1][seg_img_np > 0] = seg_bmp["colors"][1]
        seg_overlay[:, :, 2][seg_img_np > 0] = seg_bmp["colors"][2]
        seg_overlay[:, :, 3][seg_img_np > 0] = 200

    logger.info("Saving target thumbnail png ...")
    print_mem_usage()
    target_png = join(target_dir, f"{seg_series_uid}.png")
    im = Image.fromarray(base_img_np)
    im_overlay = Image.fromarray(seg_overlay)
    final_image = Image.alpha_composite(im, im_overlay)
    final_image = final_image.resize(
        (thumbnail_size, thumbnail_size), resample=Image.BICUBIC
    )
    final_image.save(target_png)
    shutil.rmtree(seg_tmp_output_dir, ignore_errors=True)
    shutil.rmtree(base_tmp_output_dir, ignore_errors=True)
    return True


def execute_command(cmd, timeout=1):
    output = run(
        cmd.split(" "),
        stdout=PIPE,
        universal_newlines=True,
        stderr=PIPE,
        timeout=timeout,
    )
    if output.returncode != 0:
        logger.error(f"############### Something went wrong with {cmd}!")
        for line in str(output).split("\\n"):
            logger.error(line)
        logger.error("##################################################")
        raise ValueError("ERROR")
    else:
        return output


if __name__ == "__main__":
    thumbnail_size = int(getenv("SIZE", "300"))
    thread_count = int(getenv("THREADS", "3"))

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

    org_image_input_dir = getenv("ORIG_IMAGE_OPERATOR_DIR", "None")
    org_image_input_dir = (
        org_image_input_dir if org_image_input_dir.lower() != "none" else None
    )
    assert org_image_input_dir is not None

    operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
    operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
    assert operator_out_dir is not None

    print("##################################################")
    print("#")
    print("# Starting Thumbnail Operator:")
    print("#")
    print(f"# thumbnail_size:      {thumbnail_size}")
    print(f"# thread_count:        {thread_count}")
    print("#")
    print(f"# workflow_dir:        {workflow_dir}")
    print(f"# batch_name:          {batch_name}")
    print(f"# operator_in_dir:     {operator_in_dir}")
    print(f"# operator_out_dir:    {operator_out_dir}")
    print(f"# org_image_input_dir: {org_image_input_dir}")
    print("#")
    print("##################################################")
    print("#")
    print("# Starting processing on BATCH-ELEMENT-level ...")
    print("#")
    print("##################################################")
    print("#")

    queue = []
    batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
    for batch_element_dir in batch_folders:
        print("#")
        print(f"# Processing batch-element {batch_element_dir}")
        print("#")
        seg_element_input_dir = join(batch_element_dir, operator_in_dir)
        orig_element_input_dir = join(batch_element_dir, org_image_input_dir)
        element_output_dir = join(batch_element_dir, operator_out_dir)

        # check if input dir present
        if not exists(seg_element_input_dir):
            print("#")
            print(f"# Input-dir: {seg_element_input_dir} does not exists!")
            print("# -> skipping")
            print("#")
            continue

        queue.append(
            (seg_element_input_dir, orig_element_input_dir, element_output_dir)
        )

    with ThreadPool(thread_count) as threadpool:
        results = threadpool.imap_unordered(create_thumbnail, queue)
        for result, input_file in results:
            print(f"#  Done: {input_file}")

    print("#")
    print("##################################################")
    print("#")
    print("# BATCH-ELEMENT-level processing done.")
    print("#")
    print("##################################################")
    print("#")

    if processed_count == 0:
        queue = []
        print("##################################################")
        print("#")
        print("# -> No files have been processed so far!")
        print("#")
        print("# Starting processing on BATCH-LEVEL ...")
        print("#")
        print("##################################################")
        print("#")

        batch_input_dir = join("/", workflow_dir, operator_in_dir)
        batch_org_image_input = join("/", workflow_dir, org_image_input_dir)
        batch_output_dir = join("/", workflow_dir, operator_in_dir)

        # check if input dir present
        if not exists(batch_input_dir):
            print("#")
            print(f"# Input-dir: {batch_input_dir} does not exists!")
            print("# -> skipping")
            print("#")
        else:
            # creating output dir
            Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        queue.append((batch_input_dir, batch_org_image_input, batch_output_dir))

        with ThreadPool(thread_count) as threadpool:
            results = threadpool.imap_unordered(create_thumbnail, queue)
            for result, input_file in results:
                print(f"#  Done: {input_file}")

        print("#")
        print("##################################################")
        print("#")
        print("# BATCH-LEVEL-level processing done.")
        print("#")
        print("##################################################")
        print("#")

    if processed_count == 0:
        print("#")
        print("##################################################")
        print("#")
        print("##################  ERROR  #######################")
        print("#")
        print("# ----> NO FILES HAVE BEEN PROCESSED!")
        print("#")
        print("##################################################")
        print("#")
        exit(1)
    else:
        print("#")
        print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
        print("#")
        print("# DONE #")
