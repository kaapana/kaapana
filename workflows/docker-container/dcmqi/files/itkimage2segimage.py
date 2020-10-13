import os
import sys
import json
import glob
import re
import math
import pandas as pd
import subprocess

def process_seg_info(seg_info, series_description):
    split_seg_info = seg_info.split('@')
    code_meaning = split_seg_info[-1]
    if len(split_seg_info) > 1:
        series_description_code_meaning = f'{code_meaning.capitalize()}-{split_seg_info[0]}'
    else:
        series_description_code_meaning = f'{code_meaning.capitalize()}'

    if series_description != "":
        return code_meaning, f'{series_description_code_meaning}-{series_description}'
    else:
        return code_meaning, series_description_code_meaning


def create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning, labelID=1):
    try:
        coding_scheme = code_lookup_table.loc[code_meaning.lower()]
    except KeyError:
        raise AssertionError(f'The specified code meaning {code_meaning.lower()} does not exist. Check here for available code names: http://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html#chapter_L from Table L-1.')

    segment_attribute = {}
    segment_attribute["labelID"] = labelID
    segment_attribute["SegmentAlgorithmType"] = segment_algorithm_type
    segment_attribute["SegmentAlgorithmName"] = segment_algorithm_name
    segment_attribute["SegmentedPropertyCategoryCodeSequence"] = {
        "CodeValue": str(coding_scheme['Code Value']),
        "CodingSchemeDesignator": coding_scheme['Coding Scheme Designator'],
        "CodeMeaning": code_meaning.capitalize()
    }
    segment_attribute["SegmentedPropertyTypeCodeSequence"] = {
        "CodeValue": str(coding_scheme['Code Value']),
        "CodingSchemeDesignator": coding_scheme['Coding Scheme Designator'],
        "CodeMeaning": code_meaning.capitalize()
    }
    segment_attribute["SegmentedPropertyTypeModifierCodeSequence"] = {
        "CodeValue": str(coding_scheme['Code Value']),
        "CodingSchemeDesignator": coding_scheme['SNOMED-RT ID (Retired)'] if not math.isnan else "unkown",
        "CodeMeaning": code_meaning.capitalize()
    }
    return segment_attribute
        
# Example: https://github.com/QIICR/dcmqi/blob/master/doc/examples/seg-example.json
# SegmentedPropertyCategoryCodeSequence: Sequence defining the general category of the property the segment represents: https://dicom.innolitics.com/ciods/rt-structure-set/rt-roi-observations/30060080/00620003
# SegmentedPropertyTypeCodeSequence: https://dicom.innolitics.com/ciods/segmentation/segmentation-image/00620002/0062000f
# Note
# "Property" is used in the sense of meaning "what the segmented voxels represent", whether it be a physical or biological object, be real or conceptual, having spatial, temporal or functional extent or not. I.e., it is what the segment "is" (as opposed to some feature, attribute, quality, or characteristic of it, like color or shape or size).
# Only a single Item shall be included in this Sequence.
# http://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html#chapter_L


print("Started: 'itkimage2segimage' ")
DCMQI = '/dcmqi/dcmqi-1.2.2-linux/bin/'


# os.environ['BATCH_NAME'] = 'batch'
# os.environ['OPERATOR_IN_DIR'] = 'initial-input'
# os.environ['WORKFLOW_DIR'] = '/home/klaus/private_data/jip-data/dcmqi/nnunet_test-200727123756236842/'

# # Case 1 single label segs with seg info
# os.environ['INPUT_TYPE'] = 'single_label_segs'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case1'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case1'
# os.environ['SINGLE_LABEL_SEG_INFO'] = 'right@kidney'

# # Case 2 single label seg info from file name
# os.environ['INPUT_TYPE'] = 'single_label_segs'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case2'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case2'
# os.environ['SINGLE_LABEL_SEG_INFO'] = 'from_file_name'

# # Case 3 Multiple single labels with creating of multi seg
# os.environ['INPUT_TYPE'] = 'single_label_segs'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case3'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case3'
# os.environ['SINGLE_LABEL_SEG_INFO'] = 'from_file_name'
# os.environ['CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS'] = 'True'

# # Case 4 Multi label label segs input
# os.environ['INPUT_TYPE'] = 'multi_label_seg'
# os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'] = 'nnunet-predict_case4'
# os.environ['OPERATOR_OUT_DIR'] = 'nrrd2dcmseg_case4'
# os.environ['MULTI_LABEL_SEG_INFO_JSON'] = 'layer_info'
# os.environ['MULTI_LABEL_SEG_NAME'] = 'example multilabel'

# If input type is set to "multi_label_seg" you must create a json inside the OPERATOR_IMAGE_LIST_INPUT_DIR that contains the parts as follows: {"seg_info": ["spleen", "right@kidney"]}

input_type = os.environ.get('INPUT_TYPE') # multi_label_seg or single_label_segs
multi_label_seg_name = os.environ.get('MULTI_LABEL_SEG_NAME', 'multi-label') # Name used for multi-label segmentation object, if it will be created
segment_algorithm_name = os.environ.get('ALGORITHM_NAME', 'kaapana')
segment_algorithm_type = os.environ.get('ALGORITHM_TYPE', 'AUTOMATIC')
content_creator_name = os.environ.get('CREATOR_NAME', 'kaapana')
series_description = os.environ.get('SERIES_DISCRIPTION', '')
series_number = os.environ.get('SERIES_NUMBER', '300')
instance_number = os.environ.get('INSTANCE_NUMBER', '1')

get_seg_info_from_file = False
if input_type == 'multi_label_seg':
    multi_label_seg_info_json = os.environ.get('MULTI_LABEL_SEG_INFO_JSON', 'seg_info.json') # name of json file that contain the parts as follows e.g. {"seg_info": ["spleen", "right@kidney"]}        
    
    if multi_label_seg_info_json == "":
        multi_label_seg_info_json = "seg_info.json"

elif input_type == 'single_label_segs':
    single_label_seg_info = os.environ.get('SINGLE_LABEL_SEG_INFO') # SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"
    create_multi_label_dcm_from_single_label_segs = os.environ.get('CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS', 'false') # true or false
    if single_label_seg_info == '':
        raise AssertionError('SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"]}')
    elif single_label_seg_info == 'from_file_name':
        print('Seg info will be taken from file name')
        get_seg_info_from_file = True
    else:
        print(f'Taking {single_label_seg_info} as seg info')
else:
    raise NameError('Input_type must be either multi_label_seg or single_label_segs')


code_lookup_table = pd.read_csv('code_lookup_table.csv', sep=';')
code_lookup_table = code_lookup_table[~code_lookup_table['Code Value'].apply(math.isnan)]
code_lookup_table['Code Meaning'] = code_lookup_table['Code Meaning'].str.lower()
code_lookup_table['Code Meaning'] = code_lookup_table['Code Meaning'].str.replace(" ", "-")
code_lookup_table = code_lookup_table.set_index('Code Meaning')
code_lookup_table['Code Value'] = code_lookup_table['Code Value'].apply(int)

batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

print("Found {} batches".format(len(batch_folders)))

for batch_element_dir in batch_folders:
    print("process: {}".format(batch_element_dir))


    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    input_image_list_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IMAGE_LIST_INPUT_DIR'])

    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    segmentation_paths = []
    for endings in ('*.nii', '*.nii.gz', '*.nrrd'):
        segmentation_paths.extend(glob.glob(f'{input_image_list_input_dir}/{endings}'))

    if len(segmentation_paths) == 0:
        print("Could not find valid segmentation file in {}".format(input_image_list_input_dir))
        print("Supported: '*.nii', '*.nii.gz', '*.nrrd'")
        print("abort!")
        exit(1)

    segmentation_information = {
        "@schema": "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/seg-schema.json#"
    }

    segmentation_information["ContentCreatorName"] = content_creator_name
    segmentation_information["SeriesNumber"] = series_number
    segmentation_information["InstanceNumber"] = instance_number

    if input_type == 'single_label_segs':
        print("input_type == 'single_label_segs'")
        
        segment_attributes = []
        for idx, seg_filepath in enumerate(segmentation_paths):
            print("process idx: {} - {}".format(idx,seg_filepath))

            seg_filename = os.path.basename(seg_filepath)
            m = re.compile(r'(.*?)(\.nii.gz|\.nii|\.nrrd)').search(seg_filename)
            rootname = m.groups()[-2]

            if get_seg_info_from_file is True:
                single_label_seg_info = rootname

            code_meaning, segmentation_information["SeriesDescription"] = process_seg_info(single_label_seg_info, series_description)
            segment_attribute = create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning)

            if create_multi_label_dcm_from_single_label_segs.lower() == 'true':
                segment_attributes.append([segment_attribute])

            segmentation_information["segmentAttributes"] = [[segment_attribute]]
            meta_data_file = f"{input_image_list_input_dir}/{rootname}.json"

            with open(meta_data_file, "w") as write_file:
                json.dump(segmentation_information, write_file)

            # Creating dcm_object
            output_dcm_file = f"{element_output_dir}/{rootname}.dcm"
            
            print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
            try:
                dcmqi_command = [
                    f"{DCMQI}/itkimage2segimage",
                    "--inputImageList", seg_filepath,
                    "--inputMetadata", meta_data_file,
                    "--outputDICOM", output_dcm_file,
                    "--inputDICOMDirectory",  element_input_dir
                ]
                print('Executing', " ".join(dcmqi_command))
                resp = subprocess.check_output(dcmqi_command, stderr=subprocess.STDOUT)
                print(resp)
            except subprocess.CalledProcessError as e:
                print('The image seems to have emtpy slices, we will skip them! This might make the segmentation no usable anymore for MITK.')
                dcmqi_command = [
                    f"{DCMQI}/itkimage2segimage",
                    "--skip",
                    "--inputImageList", seg_filepath,
                    "--inputMetadata", meta_data_file,
                    "--outputDICOM", output_dcm_file,
                    "--inputDICOMDirectory",  element_input_dir
                ]
                print('Executing', " ".join(dcmqi_command))
                resp = subprocess.check_output(dcmqi_command, stderr=subprocess.STDOUT)
                print(resp)
            except subprocess.CalledProcessError as e:
                raise AssertionError(f'Something weng wrong while creating the single-label-dcm object {e.output}')

    elif input_type == 'multi_label_seg':
        print("input_type == 'multi_label_seg'")

        json_path=os.path.join(input_image_list_input_dir, multi_label_seg_info_json)
        with open(json_path) as f:
            data = json.load(f)

        print('Loaded seg_info', data)

        if "seg_info" not in data:
            print("Could not find key 'seg_info' in json-file: {}".format(json_path))
            print("Abort!")
            exit(1)

        if "algorithm" in data:
            multi_label_seg_name = "{}-{}".format(segment_algorithm_name,data["algorithm"])

        segment_attributes = [[]]
        for idx, single_label_seg_info in enumerate(data['seg_info']):
            print("process idx: {} - {}".format(idx,single_label_seg_info))
            code_meaning, segmentation_information["SeriesDescription"] = process_seg_info(single_label_seg_info, series_description)
            segment_attribute = create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning, labelID=idx+1)
            segment_attributes[0].append(segment_attribute)
        
    if input_type == 'multi_label_seg' or create_multi_label_dcm_from_single_label_segs.lower() == 'true':
        _, segmentation_information["SeriesDescription"] = process_seg_info(multi_label_seg_name, series_description)

        segmentation_information["segmentAttributes"] = segment_attributes
        meta_data_file = f"{input_image_list_input_dir}/{multi_label_seg_name.lower()}.json"
        with open(meta_data_file, "w") as write_file:
            print("Writing JSON:: {}".format(meta_data_file))
            json.dump(segmentation_information, write_file)

        output_dcm_file = f"{element_output_dir}/{multi_label_seg_name.lower()}.dcm"
        print("Output SEG.dcm file:: {}".format(output_dcm_file))
        print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
        try:
            dcmqi_command = [
                f"{DCMQI}/itkimage2segimage",
                "--inputImageList", ",".join(segmentation_paths),
                "--inputMetadata", meta_data_file,
                "--outputDICOM", output_dcm_file,
                "--inputDICOMDirectory",  element_input_dir
            ]
            print('Executing', " ".join(dcmqi_command))
            resp = subprocess.check_output(dcmqi_command, stderr=subprocess.STDOUT)
            print(resp)
        except subprocess.CalledProcessError as e:
            print('The image seems to have emtpy slices, we will skip them! This might make the segmentation no usable anymore for MITK.')
            dcmqi_command = [
                f"{DCMQI}/itkimage2segimage",
                "--skip",
                "--inputImageList", ",".join(segmentation_paths),
                "--inputMetadata", meta_data_file,
                "--outputDICOM", output_dcm_file,
                "--inputDICOMDirectory",  element_input_dir
            ]
            print('Executing', " ".join(dcmqi_command))
            resp = subprocess.check_output(dcmqi_command, stderr=subprocess.STDOUT)
            print(resp)
        except subprocess.CalledProcessError as e:
            raise AssertionError(f'Something weng wrong while creating the multi-label-dcm object {e.output}')
    
    print("End of script.")
    print("DONE")