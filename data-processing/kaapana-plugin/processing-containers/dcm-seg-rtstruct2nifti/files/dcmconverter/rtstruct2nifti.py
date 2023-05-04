from os.path import join, exists, dirname, basename
from glob import glob
import shutil
import json
from dcmrtstruct2nii import dcmrtstruct2nii, list_rt_structs
import logging
from dcmconverter.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)
mask_background_value = 0
mask_foreground_value = 1


def convert_rtstruct(
    element_mask_dicom, element_base_dicom_in_dir, output_path, seg_filter
):
    try:
        dcmrtstruct2nii_tmp_ouput_dir = join(output_path, "tmp")
        logger.info(f"# output_path: {output_path}")
        logger.info(f"# seg_filter: {seg_filter}")
        logger.info(f"# element_mask_dicom: {element_mask_dicom}")
        logger.info(f"# element_base_dicom_in_dir: {element_base_dicom_in_dir}")

        dcmrtstruct2nii(
            rtstruct_file=element_mask_dicom,
            dicom_file=element_base_dicom_in_dir,
            output_path=dcmrtstruct2nii_tmp_ouput_dir,
            structures=None,
            gzip=True,
            mask_background_value=mask_background_value,
            mask_foreground_value=mask_foreground_value,
            convert_original_dicom=True,
            series_id=None,
        )
        generate_meta_info(dcmrtstruct2nii_tmp_ouput_dir, seg_filter)
        success = True
    except Exception as e:
        success = False

    return success


def generate_meta_info(result_dir, seg_filter):
    result_niftis = glob(join(result_dir, "*.nii.gz"), recursive=False)
    assert len(result_niftis) > 0

    seg_count = 0
    for result in result_niftis:
        seg_count += 1
        if "image.nii.gz" in result:
            continue
        target_dir = dirname(dirname(result))
        extracted_label = basename(result).replace("mask_", "").replace(".nii.gz", "")
        logger.info("#")
        if (
            seg_filter is not None
            and extracted_label.lower().replace(",", " ").replace(" ", "")
            not in seg_filter
        ):
            logger.info(
                f"# extracted_label {extracted_label.lower().replace(',',' ').replace(' ','')} not in filters {seg_filter} -> ignoring"
            )
            continue

        logger.info("#")
        file_id = f"{basename(result).split('_')[0]}_{seg_count}"
        label_string = f"--{mask_foreground_value}--{extracted_label}.nii.gz"
        new_filename = join(target_dir, f"{file_id}{label_string}")
        logger.info("#")
        logger.info("#")
        logger.info(f"# result:          {result}")
        logger.info(f"# file_id:         {file_id}")
        logger.info(f"# target_dir:      {target_dir}")
        logger.info(f"# extracted_label: {extracted_label}")
        logger.info(f"# label_string:    {label_string}")
        logger.info(f"# new_filename:    {new_filename}")
        logger.info("#")

        shutil.move(result, new_filename)

        meta_temlate = {
            "segmentAttributes": [
                [
                    {
                        "SegmentLabel": extracted_label.replace("-", " "),
                        "labelID": mask_foreground_value,
                    }
                ]
            ]
        }

        meta_path = join(dirname(new_filename), f"{file_id}-meta.json")
        with open(meta_path, "w", encoding="utf-8") as jsonData:
            json.dump(
                meta_temlate, jsonData, indent=4, sort_keys=True, ensure_ascii=True
            )

    shutil.rmtree(result_dir)
