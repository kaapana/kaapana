import sys
import os
import glob
import math
import json
import os
import re
import pydicom
from datetime import datetime
import subprocess

processed_count = 0
DCMQI = '/dcmqi/dcmqi-1.2.3-linux/bin/'

output_type = os.environ.get('OUTPUT_TYPE', 'nrrd')
seg_filter = os.environ.get('SEG_FILTER', "")
if seg_filter != "":
    seg_filter = seg_filter.lower().split(";")
    print(f"Set filters: {seg_filter}")
else:
    seg_filter = None

if output_type not in ['nrrd', 'mhd', 'mha', 'nii', 'nii.gz', 'nifti', 'hdr', 'img']:
    raise AssertionError('Output type must be <nrrd|mhd|mha|nii|nii.gz|nifti|hdr|img>')

if output_type == "nii.gz":
    output_type_dcmqi = "nii"
else:
    output_type_dcmqi = output_type

batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

print("Found {} batches".format(len(batch_folders)))

for batch_element_dir in batch_folders:
    print("process: {}".format(batch_element_dir))

    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])

    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    dcm_paths = glob.glob(f'{element_input_dir}/*.dcm')

    print("Found {} dcm-files".format(len(dcm_paths)))

    for dcm_filepath in dcm_paths:
        # Creating objects
        json_output = os.path.basename(dcm_filepath)[:-4]
        try:
            dcmqi_command = [
                f"{DCMQI}/segimage2itkimage",
                "--outputType", output_type_dcmqi,
                "-p", f'{json_output}',
                "--outputDirectory", element_output_dir,
                "--inputDICOM",  dcm_filepath
            ]
            print('Executing', " ".join(dcmqi_command))
            resp = subprocess.check_output(dcmqi_command, stderr=subprocess.STDOUT)
            print(resp)
        except subprocess.CalledProcessError as e:
            print("Error with dcmqi. Might be due to missing resources!", e.output)
            print("Abort !")
            exit(1)

        # Filtering unwanted objects
        meta_data_file = os.path.join(element_output_dir, f'{json_output}-meta.json')
        try:
            with open(meta_data_file) as f:
                meta_data = json.load(f)
        except FileNotFoundError as e:
            print("DCMQI was not successfull in converting the dcmseg object. Might be due to missing resources!", e)
            print("Abort !")
            exit(1)

        to_remove_indexes = []
        for idx, segment in enumerate(meta_data['segmentAttributes']):
            segment_info = segment[0]
            print(f"SEG-INFO: {segment_info['SegmentLabel']} -> Label: {segment_info['labelID']}")
            if seg_filter is None or segment_info['SegmentLabel'].lower() in seg_filter:
                os.rename(os.path.join(element_output_dir, f'{json_output}-{segment_info["labelID"]}.{output_type}'),
                          os.path.join(element_output_dir, f'{json_output}--{segment_info["SegmentLabel"]}.{output_type}'))
            else:
                to_remove_indexes.append(idx)
                os.remove(os.path.join(element_output_dir, f'{json_output}-{segment_info["labelID"]}.{output_type}'))

        # Updating meta-data-json
        for idx in sorted(to_remove_indexes, reverse=True):
            del meta_data['segmentAttributes'][idx]

        with open(meta_data_file, "w") as write_file:
            print("Overwriting JSON: {}".format(meta_data_file))
            json.dump(meta_data, write_file, indent=4, sort_keys=True)
        print(json.dumps(meta_data, indent=4, sort_keys=True))

        if seg_filter != None and seg_filter != "":
            len_output_files = len(sorted(glob.glob(os.path.join(element_output_dir, f"*{output_type_dcmqi}*"), recursive=False)))
            if len_output_files != len(seg_filter):
                print(f"Found {len_output_files} files -> expected {len(seg_filter)}!")
                print(f"Filter: {seg_filter}")
                print("Abort!")
                exit(1)

        processed_count += 1
        
print("#")
print("#")
print("#")
print("#")
print(f"# Processed file_count: {processed_count}")
print("#")
print("#")
if processed_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)
else:
    print("# DONE #")