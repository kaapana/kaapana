import os
import glob
import json
import os
import logging
from subprocess import PIPE, run
from os.path import join, exists, basename
from dcmconverter.logger import get_logger
logger = get_logger(__name__,logging.DEBUG)

DCMQI = '/kaapana/app/dcmqi/bin'
output_type = os.environ.get('OUTPUT_TYPE', 'nii.gz')
if output_type not in ['nrrd', 'mhd', 'mha', 'nii', 'nii.gz', 'nifti', 'hdr', 'img']:
    raise AssertionError('Output type must be <nrrd|mhd|mha|nii|nii.gz|nifti|hdr|img>')

def convert_dcmseg(element_mask_dicom, element_base_dicom_in_dir, output_path, seg_filter):

    json_output = basename(element_mask_dicom)[:-4]
    dcmqi_command = [
        f"{DCMQI}/segimage2itkimage",
        "--outputType", output_type if output_type != "nii.gz" else "nii",
        "-p", f'{json_output}',
        "--outputDirectory", output_path,
        "--inputDICOM",  element_mask_dicom
    ]
    logger.info(f"# DCMQI COMMAND: {dcmqi_command}")
    output = run(dcmqi_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=120)
    logger.info("# DCMQI stdout:")
    logger.info(output.stdout)
    if output.returncode != 0:
        logger.error("# Something went wrong within the DCMQI mask conversion!")
        logger.error("# DCMQI stderr:")
        logger.error(output.stderr)
        return False

    meta_data_file = join(output_path, f'{json_output}-meta.json')
    try:
        with open(meta_data_file) as f:
            meta_data = json.load(f)
    except FileNotFoundError as e:
        logger.error("DCMQI was not successfull in converting the dcmseg object. Might be due to missing resources!", e)
        logger.error("Abort !")
        exit(1)

    to_remove_indexes = []
    for idx, segment in enumerate(meta_data['segmentAttributes']):
        segment_info = segment[0]
        segment_label = segment_info['SegmentLabel'].lower()
        logger.info(f"SEG-INFO: {segment_label} -> Label: {segment_info['labelID']}")
        if seg_filter is None or segment_label.lower().replace(","," ").replace("  "," ") in seg_filter:
            segment_label = segment_label.replace("/", "++")
            os.rename(join(output_path, f'{json_output}-{segment_info["labelID"]}.{output_type}'),join(output_path, f'{json_output}--{segment_info["labelID"]}--{segment_label}.{output_type}'))
        else:
            to_remove_indexes.append(idx)
            os.remove(join(output_path, f'{json_output}-{segment_info["labelID"]}.{output_type}'))

    # Updating meta-data-json
    for idx in sorted(to_remove_indexes, reverse=True):
        del meta_data['segmentAttributes'][idx]

    with open(meta_data_file, "w") as write_file:
        json.dump(meta_data, write_file, indent=4, sort_keys=True)

    if seg_filter != None and seg_filter != "":
        len_output_files = len(sorted(glob.glob(join(output_path, f"*{output_type}*"), recursive=False)))
        if len_output_files != len(seg_filter):
            logger.info(f"Found {len_output_files} files -> expected {len(seg_filter)}!")
            logger.info(f"Filter: {seg_filter}")
    return True
    

