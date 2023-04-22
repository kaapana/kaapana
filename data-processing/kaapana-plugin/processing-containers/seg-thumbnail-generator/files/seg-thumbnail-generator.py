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
from random import randint

logger = None
processed_count = 0
execution_timeout = 10


def print_mem_usage(msg=None):
    if msg is None:
        msg = "Memory usage"
    logger.info(
        f"{msg}: {round(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)} MB"
    )


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

    img_array = np.array(img_array)
    if np.max(img_array) <= 1:
        img_array = img_array.astype("bool")

    return img_array


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
        execute_command(cmd=modality_cmd, timeout=10)
        .stdout.split("\n")[0]
        .split(" ")[2]
        .replace("[", "")
        .replace("]", "")
    )
    seg_series_uid_cmd = f"dcmdump {seg_dcm} --prepend --load-short --search 0020,000E"
    seg_series_uid = execute_command(cmd=seg_series_uid_cmd, timeout=10).stdout.split(
        "\n"
    )
    seg_series_uid = [x for x in seg_series_uid if ".(0020,000e)" not in x and x != ""]
    assert len(seg_series_uid) == 1
    seg_series_uid = seg_series_uid[0].split(" ")[2].replace("[", "").replace("]", "")
    logger.info("Scanning base images ...!")
    print_mem_usage()

    scan_direction = None
    base_series_uids = {}
    for index, base_dcm in enumerate(base_input_files):
        if scan_direction is None:
            scan_dir_cmd = f"dcmdump {base_dcm} --search 0018,5100"
            scan_direction = execute_command(cmd=scan_dir_cmd, timeout=10)
            scan_direction = (
                scan_direction.stdout.replace("  ", "")
                .replace("#", "")
                .split(" ")[2]
                .replace("[", "")
                .replace("]", "")
            )

        object_uid_cmd = f"dcmdump {base_dcm} --search 0008,0018"
        object_uid = execute_command(cmd=object_uid_cmd, timeout=10)
        object_uid = (
            object_uid.stdout.replace("  ", "")
            .split(" ")[2]
            .replace("[", "")
            .replace("]", "")
        )
        object_uid_cmd = f"dcmdump {base_dcm} --search 0008,0018"
        object_uid = execute_command(cmd=object_uid_cmd, timeout=10)
        object_uid = (
            object_uid.stdout.replace("  ", "")
            .split(" ")[2]
            .replace("[", "")
            .replace("]", "")
        )
        slice_index_cmd = f"dcmdump {base_dcm} --search 0020,0013"
        slice_index = execute_command(cmd=slice_index_cmd, timeout=10)
        slice_index = int(
            slice_index.stdout.split(" ")[2].replace("[", "").replace("]", "")
        )
        if scan_direction[0].lower() == "f" or scan_direction.lower() == "hfs":
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
            path_rtstruct_dcm=seg_dcm,
            seg_series_uid=seg_series_uid,
            dcm_dir=dcm_dir,
            base_series_uids=base_series_uids,
            target_dir=target_dir,
        )

    elif modality == "SEG":
        logger.info("modality == SEG")
        print_mem_usage()
        result = create_seg_thumbnail(
            seg_dcm, base_series_uids, target_dir, seg_series_uid
        )

    else:
        logger.error(f"modality == {modality} -> Error!")
        return False, dcm_seg_dir
    if not result:
        logger.error("Something went wrong!")
        print_mem_usage()
        return False, dcm_seg_dir
    else:
        processed_count += 1
        return True, dcm_seg_dir


def create_rtstruct_thumbnail(
    path_rtstruct_dcm, seg_series_uid, dcm_dir, base_series_uids, target_dir
):
    logger.info("In create_rtstruct_thumbnail ...")
    print_mem_usage()

    def parse_value(raw):
        value = raw.split("[")[1].split("]")[0]
        if "\\" in value:
            value = [int(x) for x in value.split("\\")]
        return value

    logger.info("Executing dcmdump ...")
    print_mem_usage()
    dcmdump_rtstruct_cmd = f"dcmdump {path_rtstruct_dcm}"
    dcmdump = execute_command(cmd=dcmdump_rtstruct_cmd, timeout=10)
    dcmdump = dcmdump.stdout.split("\n")

    logger.info("dcmdump loaded ...")
    print_mem_usage()
    rois = {}
    ref_uids_dict = {}
    base_image_uid = None
    sequenz_count = 0
    for index, line in enumerate(dcmdump):
        if "ROINumber" in line:
            if "ROIName" in dcmdump[index + 2]:
                roi_number = int(parse_value(line))
                assert roi_number not in rois
                rois[roi_number] = {"name": parse_value(dcmdump[index + 2])}

        elif "ReferencedFrameOfReferenceUID" in line:
            ref_image_uid = parse_value(line)
            if base_image_uid is not None:
                assert base_image_uid == ref_image_uid
            base_image_uid = ref_image_uid

        elif "ROIDisplayColor" in line:  # ROI Color
            roi_color = parse_value(line)
            roi_number_found = False
            if "ContourSequence" in dcmdump[index + 1]:
                sequenz_count += 1
                sequenzes = []
                for sub_index, sub_line in enumerate(dcmdump[index + 1 :]):
                    if "ReferencedSOPInstanceUID" in sub_line:
                        if (
                            "ContourData" in dcmdump[index + 1 :][sub_index + 5]
                            or "ContourData" in dcmdump[index + 1 :][sub_index + 6]
                        ):
                            ref_uid = parse_value(sub_line)
                            sequenzes.append(ref_uid)
                        else:
                            pass
                    if "ReferencedROINumber" in sub_line:
                        roi_number_found = True
                        roi_ref = int(parse_value(sub_line))
                        rois[roi_ref]["color"] = roi_color
                        rois[roi_ref]["sequenzes"] = sequenzes
                        for req_sequenz in sequenzes:
                            if req_sequenz not in ref_uids_dict:
                                ref_uids_dict[req_sequenz] = []
                            if rois[roi_ref]["name"] not in ref_uids_dict[req_sequenz]:
                                ref_uids_dict[req_sequenz].append(rois[roi_ref]["name"])
                        break
                    if "ROIDisplayColor" in sub_line:
                        break
            elif "ReferencedROINumber" in dcmdump[index + 1]:
                roi_number_found = True
                roi_ref = int(parse_value(dcmdump[index + 1]))
                rois[roi_ref]["color"] = roi_color
                rois[roi_ref]["sequenzes"] = []

    logger.info("RTSTRUCT has been analized ...")
    print_mem_usage()
    dcmdump = None

    assert roi_number_found
    ref_uids_dict = {
        k: v
        for k, v in sorted(
            ref_uids_dict.items(), key=lambda item: len(item[1]), reverse=True
        )
    }
    correct_slice_uid = list(ref_uids_dict.keys())[0]
    base_dcm_file = base_series_uids[correct_slice_uid]

    label_ids = list(set(ref_uids_dict[correct_slice_uid]))
    label_info = {}
    for id, roi in rois.items():
        label_info[roi["name"]] = roi["color"]
    rois = None
    ref_uids_dict = None

    slice_index = base_dcm_file["slice_index"]
    logger.info(f"Best slice identified: {slice_index}")

    logger.info("Reading RTSTRUCT ...")
    print_mem_usage()
    try:
        rtstruct = RTStructBuilder.create_from(
            dicom_series_path=dcm_dir, rt_struct_path=path_rtstruct_dcm
        )
    except Exception as e:
        logger.error("Something went wrong!")
        logger.error(f"Error: {e}")
        return False

    logger.info("Collecting slice masks ...")
    print_mem_usage()
    seg_overlay = None
    seg_overlay_slices_list = []
    for index, roi_name in enumerate(rtstruct.get_roi_names()):
        logger.info(f"Processing: {roi_name} ...")
        print_mem_usage()
        if roi_name not in label_ids:
            logger.info(f"{roi_name} not in list --> skipping")
            logger.info("")
            continue

        color = label_info[roi_name]
        try:
            mask_3d = rtstruct.get_roi_mask_by_name(roi_name).astype("bool")[
                :, :, slice_index
            ]
            logger.info("3D mask loaded ...")
            print_mem_usage()
            pixel_count = int(np.sum(mask_3d))
            if pixel_count == 0:
                logger.info(
                    f"{roi_name} no annotation found in slice {slice_index} --> skipping"
                )
                logger.info("")
                continue
            seg_overlay_slices_list.append([pixel_count, color, mask_3d])
            logger.info("")
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

    logger.info("Mask parsing done ...")
    print_mem_usage()
    logger.info("")
    seg_overlay = np.zeros((mask_3d.shape[0], mask_3d.shape[1], 4), dtype="uint8")
    mask_3d = None
    rtstruct = None
    seg_overlay_slices_list = sorted(
        seg_overlay_slices_list, key=lambda x: x[0], reverse=True
    )
    logger.info(f"Generating overlay ...")
    print_mem_usage()
    logger.info("")
    for label_mask in seg_overlay_slices_list:
        pixel_count = label_mask[0]
        color = label_mask[1]
        label_mask = label_mask[2]
        seg_overlay[:, :, 0][label_mask > 0] = color[0]
        seg_overlay[:, :, 1][label_mask > 0] = color[1]
        seg_overlay[:, :, 2][label_mask > 0] = color[2]
        seg_overlay[:, :, 3][label_mask > 0] = 200

    seg_overlay_slices_list = None

    logger.info(f"Overlay created.")
    print_mem_usage()
    logger.info("")
    base_dcm_path = base_dcm_file["base_dcm"]

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
    logger.info("Creating final thumbnail ...")
    print_mem_usage()
    logger.info("")

    im_overlay = Image.fromarray(seg_overlay)
    final_image = Image.alpha_composite(im, im_overlay)
    final_image = final_image.resize(
        (thumbnail_size, thumbnail_size), resample=Image.BICUBIC
    )
    final_image.save(target_png)
    shutil.rmtree(join(target_dir, "tmp"), ignore_errors=True)
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
    seg_img_info = [x for x in seg_img_info if "(5200,9230)" in x and x != ""]

    seg_ref_image_info_cmd = (
        f"dcmdump {seg_dcm} --prepend --load-short --search 0008,1155"
    )
    logger.info("Get seg_ref_img_info ...")
    print_mem_usage()
    seg_ref_img_info = execute_command(cmd=seg_ref_image_info_cmd, timeout=10)
    seg_ref_img_info = seg_ref_img_info.stdout.split("\n")
    seg_ref_img_info = [
        x
        for x in seg_ref_img_info
        if (
            "(5200,9230)" in x
            or "(0008,1200).(0008,1115).(0008,114a).(0008,1155) UI" in x
        )
        and x != ""
    ]

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
    tmp_rand_colors = {}
    seg_id_list = []
    for index, info in enumerate(seg_img_info):
        if info == "":
            continue
        info = info.split(" ")[2].replace("#", "").split("\\")
        seg_id = int(info[0]) - 1
        if seg_id not in seg_id_list:
            seg_id_list.append(seg_id)
        if len(dicomlab_color_img_info) > 0:
            dicomlab = dicomlab_color_img_info[seg_id].split(" ")[2].split("\\")
            dicomlab = [float(int(x)) for x in dicomlab]
            color_rgb = dicomlab2LAB(dicomlab=dicomlab)
            lab = LabColor(color_rgb[0], color_rgb[1], color_rgb[2])
            color_rgb = convert_color(lab, sRGBColor).get_upscaled_value_tuple()
            color_rgb = [max(min(x, 255), 0) for x in color_rgb]
        else:
            if str(seg_id) not in tmp_rand_colors:
                logger.warning(
                    f"No color information could be found -> using random colors for seg_id {seg_id} ..."
                )
                color_rgb = [randint(0, 255), randint(0, 255), randint(0, 255)]
                tmp_rand_colors[str(seg_id)] = color_rgb
            else:
                color_rgb = tmp_rand_colors[str(seg_id)]
        slice_ref = (
            seg_ref_img_info[index].split(" ")[2].replace("[", "").replace("]", "")
        )
        assert slice_ref in base_series_uids
        base_series_uids[slice_ref]["seg_bmps"].append(
            {"bmp_file": seg_bmps[index], "colors": color_rgb}
        )

    logger.info("Identify best thumbnail slice ...")
    print_mem_usage()
    slice_max_id = None
    max_pixel_count = 0
    slice_max_segs = 0

    if len(seg_id_list) > 1:
        logger.info("Multi-seg method ...")
    else:
        logger.info("Single-seg method ...")

    for index, base_slice in enumerate(base_series_uids):
        base_slice_element = base_series_uids[base_slice]
        if len(seg_id_list) > 1:
            if len(base_slice_element["seg_bmps"]) > slice_max_segs:
                slice_max_id = base_slice
                slice_max_segs = len(base_slice_element["seg_bmps"])
        else:
            base_slice_element = base_series_uids[base_slice]
            assert len(base_slice_element["seg_bmps"]) == 1
            seg_img_path = base_slice_element["seg_bmps"][0]["bmp_file"]
            logger.info(f"Loading seg bmp: {basename(seg_img_path)}")
            seg_img_np = load_img(img_path=seg_img_path, rgba=False)
            pixel_count = int(np.sum(seg_img_np))
            if pixel_count > max_pixel_count:
                max_pixel_count = pixel_count
                slice_max_id = base_slice

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
    shutil.rmtree(join(target_dir, "tmp"), ignore_errors=True)
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
    # os.environ["WORKFLOW_DIR"] = "/home/jonas/thumb-test/8/"
    # os.environ["BATCH_NAME"] = "batch"
    # os.environ["OPERATOR_IN_DIR"] = "get-input-data"
    # os.environ["ORIG_IMAGE_OPERATOR_DIR"] = "get-ref-series-ct"
    # os.environ["OPERATOR_OUT_DIR"] = "generate-segmentation-thumbnail"
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
        if not result:
            exit(1)

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
