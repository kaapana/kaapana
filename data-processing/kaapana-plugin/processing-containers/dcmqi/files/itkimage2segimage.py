import os
import json
import glob
import re
import math
import random
from matplotlib import cm
import subprocess
import numpy as np
import pydicom

from pathlib import Path
processed_count = 0


def find_code_meaning(tag):
    result = None
    print("#####################################################")
    print("#")
    print(f"Searching for identical hit for {tag}...")
    tag = tag.lower()
    for entry in code_lookup_table:
        if tag.replace(" ", "-") == entry["Code Meaning"].lower().replace(" ", "-"):
            print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag}")
            result = entry
            break
        elif tag == entry["Body Part Examined"].lower():
            print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag}")
            result = entry
            break

    if result == None:
        print(f"Nothing found -> Searching if {tag} is in one of the entires...")
        for entry in code_lookup_table:
            if tag in entry["Code Meaning"].lower():
                print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag}")
                result = entry
                break
            elif tag in entry["Body Part Examined"].lower():
                print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag}")
                result = entry
                break

    if result == None:
        print(f"Nothing found -> Searching if {tag} parts equals one of the entires...")
        for entry in code_lookup_table:
            for tag_part in tag.split(" "):
                if tag_part == entry["Code Meaning"].lower():
                    print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
                elif tag_part == entry["Body Part Examined"].lower():
                    print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
            if result != None:
                break

    if result == None:
        print(f"Nothing found -> Searching if {tag} parts can be found in one of the entires...")
        for entry in code_lookup_table:
            for tag_part in tag.split(" "):
                if tag_part in entry["Code Meaning"].lower():
                    print(f"Found Code Meaning: {entry['Code Meaning'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
                elif tag_part in entry["Body Part Examined"].lower():
                    print(f"Found Code Meaning: {entry['Body Part Examined'].lower()} for search term: {tag_part.lower()}")
                    result = entry
                    break
            if result != None:
                break

    if result == None:
        print(f"Could not find the tag: '{tag}' in the lookup table, using custom entry")
        result = {
            "Coding Scheme Designator": "Custom",
            "Code Value": "0.0.0.0.0.0.00000.0.000.0.00",
            "Code Meaning": f"{tag.replace('  ', ' '). lower()}",
            "Body Part Examined": "",
            "SNOMED-RT ID (Retired)": "",
            "FMA Code Value": None,
            "UMLS Concept UniqueID": ""
        }

    print("#")
    print("#####################################################")
    return result


def process_seg_info(seg_info, series_description):
    code_meaning = str(seg_info).lower()
    series_description_code_meaning = f'{code_meaning}'

    if series_description != "":
        return code_meaning, series_description
    else:
        return code_meaning, series_description_code_meaning


def create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning, color, label_name="", labelID=1):
    try:
        search_key = code_meaning.split("@")[-1].lower() if "@" in code_meaning else code_meaning
        print("Searching coding-scheme for code-meaning: {}".format(code_meaning))
        print("Search-key: {}".format(search_key))
        coding_scheme = find_code_meaning(tag=search_key)
    except KeyError:
        raise AssertionError(
            f'The specified code meaning {code_meaning.lower()} does not exist. Check here for available code names: http://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html#chapter_L from Table L-1.')

    segment_attribute = {}
    segment_attribute["labelID"] = labelID
    segment_attribute["SegmentAlgorithmType"] = segment_algorithm_type
    segment_attribute["SegmentAlgorithmName"] = segment_algorithm_name
    segment_attribute["recommendedDisplayRGBValue"] = color

    # segment_attribute["SegmentNumber"] = labelID
    segment_attribute["SegmentLabel"] = label_name
    segment_attribute["SegmentedPropertyCategoryCodeSequence"] = {
        "CodeValue": str(coding_scheme['Code Value']),
        "CodingSchemeDesignator": coding_scheme['Coding Scheme Designator'],
        "CodeMeaning": code_meaning
    }
    segment_attribute["SegmentedPropertyTypeCodeSequence"] = {
        "CodeValue": str(coding_scheme['Code Value']),
        "CodingSchemeDesignator": coding_scheme['Coding Scheme Designator'],
        "CodeMeaning": code_meaning
    }
    segment_attribute["SegmentedPropertyTypeModifierCodeSequence"] = {
        "CodeValue": str(coding_scheme['Code Value']),
        "CodingSchemeDesignator": coding_scheme['SNOMED-RT ID (Retired)'] if not math.isnan else "unkown",
        "CodeMeaning": code_meaning
    }
    return segment_attribute


def adding_aetitle(element_input_dir, output_dcm_file, body_part):
    dcm_files = sorted(glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True))

    if len(dcm_files) == 0:
        print("No dicom file found!")
        exit(1)

    dcm_file = dcm_files[0]
    print("dcm-file: {}".format(dcm_file))
    input_dicom = pydicom.dcmread(dcm_file)
    try:
        aetitle = input_dicom[0x0012, 0x0020].value
    except KeyError:
        aetitle = 'internal'
    try:
        dicom_body_part = input_dicom[0x0018, 0x0015].value
    except KeyError:
        dicom_body_part = None

    dcmseg_file = pydicom.dcmread(output_dcm_file)
    print(f"# Adding aetitle:   {aetitle}")
    if body_part == "N/A" and dicom_body_part is not None:
        print(f"# Adding dicom-body_part: {dicom_body_part}")
        dcmseg_file.add_new([0x0018, 0x0015], 'LO', dicom_body_part)  # Body Part Examined
    elif body_part != "N/A":
        print(f"# Adding model-body_part: {body_part}")
        dcmseg_file.add_new([0x0018, 0x0015], 'LO', body_part)  # Body Part Examined
    else:
        print("# Could not extract any body-part!")

        # dataset = self.workflow_conf.get("workflow_form").get("data_dir")
        
        self.convert_dataset(Path(self.root_dir)/self.data_dir, self.meta_data)

    # config_file = Path(batch_element_dir)/ os.environ.get("OPERATOR_IMAGE_LIST_INPUT_DIR")/'seg_args.json'
    config_file = "/data/conf/conf.json"
    try:
        with open(config_file, 'r') as f:
            config_json = json.load(f)
        config = config_json["seg_args"]
        valid_keys = [
            "INPUT_TYPE", 
            "SINGLE_LABEL_SEG_INFO",
            "CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS",
            "MULTI_LABEL_SEG_INFO_JSON",
            "MULTI_LABEL_SEG_NAME",
            "SERIES_DISCRIPTION",
            "ALGORITHM_NAME",
            "CREATOR_NAME",
            "ALGORITHM_TYPE",
            "SERIES_NUMBER",
            "INSTANCE_NUMBER",
            "SKIP_EMPTY_SLICES",
            "DCMQI_COMMAND",
            "OPERATOR_IMAGE_LIST_INPUT_DIR"]

        for k,v in config.items():
            key = k.upper()
            if key not in valid_keys:
                raise NameError(f"Arguments in 'seg_args.json' is invalid. Valid keys are {valid_keys}")
            os.environ[key] = v
        print("Found args.json in segmentation folder. parameters given by dag will be overwritten.")
    except FileNotFoundError:
        print("No args.json found. Continuing with parameters from dag definition.")



set_args_from_config()

print("Started: 'itkimage2segimage' ")
DCMQI = '/kaapana/app/dcmqi/bin'


# os.environ['BATCH_NAME'] = 'batch'
# os.environ['OPERATOR_IN_DIR'] = 'input'
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

input_type = os.environ.get('INPUT_TYPE')  # multi_label_seg or single_label_segs
multi_label_seg_name = os.environ.get('MULTI_LABEL_SEG_NAME') if os.environ.get('MULTI_LABEL_SEG_NAME') not in [None, "None", ''] else 'multi-label'  # Name used for multi-label segmentation object, if it will be created
segment_algorithm_name = os.environ.get('ALGORITHM_NAME', 'kaapana')
segment_algorithm_type = os.environ.get('ALGORITHM_TYPE', 'AUTOMATIC')
content_creator_name = os.environ.get('CREATOR_NAME', 'kaapana')
series_description = os.environ.get('SERIES_DISCRIPTION', '')
series_number = os.environ.get('SERIES_NUMBER', '300')
instance_number = os.environ.get('INSTANCE_NUMBER', '1')
skip_empty_slices = True if os.environ.get('SKIP_EMPTY_SLICES', 'false').lower() == "true" else False

get_seg_info_from_file = False
if input_type == 'multi_label_seg':
    multi_label_seg_info_json = os.environ.get('MULTI_LABEL_SEG_INFO_JSON', 'seg_info.json')  # name of json file that contain the parts as follows e.g. {"seg_info": ["spleen", "right@kidney"]}

    if multi_label_seg_info_json == "":
        multi_label_seg_info_json = "seg_info.json"

elif input_type == 'single_label_segs':
    single_label_seg_info = os.environ.get('SINGLE_LABEL_SEG_INFO')  # SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"
    create_multi_label_dcm_from_single_label_segs = os.environ.get('CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS', 'false')  # true or false
    if single_label_seg_info == '':
        raise AssertionError('SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"]}')
    elif single_label_seg_info == 'from_file_name':
        print('Seg info will be taken from file name')
        get_seg_info_from_file = True
    else:
        print(f'Taking {single_label_seg_info} as seg info')
else:
    raise NameError('Input_type must be either multi_label_seg or single_label_segs')


code_lookup_table_path = "code_lookup_table.json"
with open(code_lookup_table_path) as f:
    code_lookup_table = json.load(f)

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

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
        print("skipping!")
        # exit(1)
        continue

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
            print(f"process idx: {idx} - {seg_filepath}")

            seg_filename = os.path.basename(seg_filepath)
            m = re.compile(r'(.*?)(\.nii.gz|\.nii|\.nrrd)').search(seg_filename)
            rootname = m.groups()[-2]

            if get_seg_info_from_file is True:
                single_label_seg_info = rootname

            code_meaning, segmentation_information["SeriesDescription"] = process_seg_info(single_label_seg_info, series_description)
            color = np.round(np.array(cm.get_cmap('gist_ncar', 20)(random.randint(0, 19))[:3])*255).astype(int).tolist()
            segment_attribute = create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning, color)

            if create_multi_label_dcm_from_single_label_segs.lower() == 'true':
                segment_attributes.append([segment_attribute])

            segmentation_information["segmentAttributes"] = [[segment_attribute]]
            meta_data_file = f"{input_image_list_input_dir}/{rootname}.json"

            with open(meta_data_file, "w") as write_file:
                json.dump(segmentation_information, write_file, indent=4, sort_keys=True)

            # Creating dcm_object
            output_dcm_file = f"{element_output_dir}/{rootname}.dcm"

            print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
            print(f"skip_empty_slices: {skip_empty_slices}")
            if skip_empty_slices:
                try:
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
            else:
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
                    print(f'The image seems to have empty slices, we will skip them! This might make the segmentation no usable anymore for MITK. Error: {e.output}')
                    raise AssertionError(f'Something weng wrong while creating the single-label-dcm object {e.output}')

            adding_aetitle(element_input_dir, output_dcm_file, body_part="N/A")
            processed_count += 1

    elif input_type == 'multi_label_seg':
        print("input_type == 'multi_label_seg'")

        json_path = os.path.join(input_image_list_input_dir, multi_label_seg_info_json)
        with open(json_path) as f:
            data = json.load(f)

        print('Loaded seg_info', data)

        if "seg_info" not in data:
            print("Could not find key 'seg_info' in json-file: {}".format(json_path))
            print("Abort!")
            exit(1)

        label_info = data['seg_info']

        body_part = "N/A"
        if "task_body_part" in data:
            body_part = data['task_body_part']

        if "algorithm" in data:
            series_description = "{}-{}".format(segment_algorithm_name, data["algorithm"])

        segment_attributes = [[]]

        label_counts = len(label_info)
        for idx, label in enumerate(label_info):
            label_int = int(label["label_int"])
            single_label_seg_info = label["label_name"]
            print(f"process: {single_label_seg_info}: {label_int}")
            if str(label_int) == "0":
                print("Clear Label -> skipping")
                continue

            code_meaning, segmentation_information["SeriesDescription"] = process_seg_info(single_label_seg_info, series_description)
            color = np.round(np.array(cm.get_cmap('gist_ncar', label_counts)(idx)[:3])*255).astype(int).tolist()
            segment_attribute = create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning, color, label_name=single_label_seg_info, labelID=label_int)
            segment_attributes[0].append(segment_attribute)

    if input_type == 'multi_label_seg' or create_multi_label_dcm_from_single_label_segs.lower() == 'true':
        _, segmentation_information["SeriesDescription"] = process_seg_info(multi_label_seg_name, series_description)

        segmentation_information["segmentAttributes"] = segment_attributes
        meta_data_file = f"{input_image_list_input_dir}/{multi_label_seg_name.lower()}.json"
        with open(meta_data_file, "w") as write_file:
            print("Writing JSON:: {}".format(meta_data_file))
            json.dump(segmentation_information, write_file, indent=4, sort_keys=True)

        output_dcm_file = f"{element_output_dir}/{multi_label_seg_name.lower()}.dcm"
        print("Output SEG.dcm file:: {}".format(output_dcm_file))
        print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
        print(f"skip_empty_slices: {skip_empty_slices}")
        if skip_empty_slices:
            try:
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
        else:
            assert(isinstance(study_instance_UIDs, list))
            assert(len(study_instance_UIDs) == len(patients))

        
        series_descriptions = meta_data.get("Series Descriptions") if meta_data.get("Series descriptions") else [None for _ in range(len(cases))]
        added_tags = meta_data.get("add_tags")
        
        seg_args = None
        seg_path = None
        # check if there are volumes with associated segmentations
        if any([s != None for _, s in cases]):
            # check if there are seg_args in meta_data
            try:
                seg_args = meta_data['seg_args']
                seg_path = path/seg_args['multi_label_seg_info_json'] if seg_args['multi_label_seg_info_json'] else None

                # print("### Checking for segmentation information.")
                if seg_args is not None:
                    print("### Extracting parameters for segmentation converter.")                    
                    self.workflow_conf["seg_args"] = seg_args
                    with open("/data/conf/conf.json", 'w+') as conf_file:
                        # conf = json.load(conf_file)
                        json.dump(self.workflow_conf, conf_file)
                print("### Processing segmentation parameters finished.")
            except KeyError:
                print("No arguments for Itk2DcmSegOperator found. Please provide 'seg_args' in the 'meta_data.json'.")
                seg_args = make_seg_args()

        for i, case in enumerate(cases):
            series_tag_values = {}
            # series_tag_values["0020|0010"] = # study_id
            series_tag_values["0020|000d"] = study_instance_UIDs[i]
            series_tag_values["0020|0011"] = str(i)
            if added_tags is not None:
                for p in added_tags.keys():
                    p = f"/{p}" if p[0] != "/" else p
                    if str(case[0]) in glob.glob(f"{str(path)}{p}"):
                        series_tag_values= {**series_tag_values, **added_tags[p]}

            self.convert_series(
                Path(case[0]), 
                patient_id=patients[i], 
                series_description=series_descriptions[i], 
                modality=self.modality, 
                series_tag_values=series_tag_values,
                seg_args=seg_args,
                segmentation=case[1],
                seg_info_path=seg_path or None
            )
        

    def convert_series(self, case_path, patient_id, series_tag_values, segmentation=None, seg_info_path=None, *args, **kwds):
        """
        :param data: data to process given as list of paths of the ".nii.gz" files to process.
        
        :returns: None type. Writes dicoms to $OPERATOR_OUT_DIR.
        """
        series_id = str(case_path).split('/')[-1].split('.')[0]
        series_description = kwds.get("series_description")
        dataset = str(case_path).split('/')[-2]
        if series_description == None:
            series_description = f"{str(case_path).split('/')[-2]}-{series_id}-{patient_id}"
    
        modality = kwds.get("modality") or "OT"
        if modality == "OT":
            warnings.warn("Modality is 'other' (OT). Unspecific modality does not not support correct representation of translation and rotation.", UserWarning)


        study_uid = series_tag_values['0020|000d']
        series_instance_UID = kwds.get("series_uid") or generate_uid(entropy_srcs=[patient_id, study_uid, series_id, self.seed])
        out_dir = make_out_dir(series_instance_UID, dataset=dataset, case=series_id, segmentation=segmentation, human_readable=False)

        new_img = sitk.ReadImage(case_path) 
        modification_time = time.strftime("%H%M%S")
        modification_date = time.strftime("%Y%m%d")

        direction = new_img.GetDirection()
        
        if "0008|0008" in series_tag_values.keys():
            pass
        else:
            series_tag_values["0008|0008"] = "DERIVED\\SECONDARY" # Image Type

        series_tag_values["0008|0031"] = modification_time # Series Time
        series_tag_values["0008|0021"] = modification_date # Series Date
        series_tag_values["0020|0037"] = '\\'.join(map(str, (direction[0], direction[3], direction[6], direction[1],direction[4],direction[7])))
        series_tag_values["0008|103e"] = series_description # Series Description
        series_tag_values["0020|000e"] = series_instance_UID
        series_tag_values["0008|0060"] = modality
        series_tag_values["0010|0020"] = patient_id
        
        
        castFilter = sitk.CastImageFilter()
        castFilter.SetOutputPixelType(sitk.sitkInt16)
        imgFiltered = castFilter.Execute(new_img)
        
        for i in range(imgFiltered.GetDepth()):
            self.write_slices(imgFiltered, series_tag_values, i, out_dir/'dicoms')
        print("***", out_dir, "written.")
        

        if segmentation:
            print("### Checking for segmentation information.")
            shutil.copy2(segmentation, out_dir/'segmentations/')
            # if seg_args is not None:
            # print("### Copying segmentatin file.")

            if seg_info_path:
                print("### Passing seg_info.json to segmentation converter.")
                #study_dir = '/'.join(str(path).split('/')[:-1])
                shutil.copy2(seg_info_path, out_dir/'segmentations/')
        #     print("### Processing segmentation parameters finished.")
            

    def write_slices(self, new_img, series_tag_values, i, out_dir):
        image_slice = new_img[:,:,i]
        writer = sitk.ImageFileWriter()
        writer.KeepOriginalImageUIDOn()
        
        patient_id = series_tag_values["0010|0020"]
        study_uid = series_tag_values["0020|000d"]
        series_uid = series_tag_values["0020|000e"]

        prefix = ".".join(series_uid.split(".")[:4])+"." # ugly syntax for strap the prefix from the series uid and reuse it for slice identifier but w/e
        slice_instance_uid = generate_uid(prefix=prefix, entropy_srcs=[patient_id, study_uid, series_uid, str(i), self.seed])

        series_tag_values["0008|0018"] = slice_instance_uid

        # set metadata shared by series
        for tag, value in series_tag_values.items():
            image_slice.SetMetaData(tag, value)

        # set slice specific metadata tags.
        image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d")) # Instance Creation Date
        image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S")) # Instance Creation Time

        # (0020, 0032) image position patient determines the 3D spacing between slices.
        image_slice.SetMetaData("0020|0032", '\\'.join(map(str,new_img.TransformIndexToPhysicalPoint((0,0,i))))) # Image Position (Patient)
        image_slice.SetMetaData("0020|0013", str(i)) # Instance Number

        # Write to the output directory and add the extension dcm, to force writing in DICOM format.
        writer.SetFileName(os.path.join(out_dir,'slice' + str(i).zfill(4) + '.dcm'))
        writer.Execute(image_slice)



class Parser:
    """Parser for nifti or nrrd files. Lists all cases to process within a certain directory, along with the respective segmentation files. 
    Can be overwritten to support custom file trees.
    """
    def __init__(self) -> None:
        pass

    def __call__(self, path, *args, **kwds):
        def get_depth(path, depth=0):
            if not os.path.isdir(path): return depth
            maxdepth = depth
            for entry in os.listdir(path):
                fullpath = os.path.join(path, entry)
                maxdepth = max(maxdepth, get_depth(fullpath, depth + 1))
            return maxdepth
    
        if os.path.isdir(os.path.join(path, "cases")) and os.path.isdir(os.path.join(path, "segs")):
            return self.parse_by_structure(path, *args, **kwds)
        elif get_depth(path) == 1:
            return self.parse_combined_dir(path, *args, **kwds)
        else:
            raise FileNotFoundError("Could not parse file structure, please verify input data.")
        

    def parse_combined_dir(self,path, *args, **kwds):
        
        cases = [f for f in Path(path).rglob("*") if (re.match(r'^(?!.*(?:seg|Seg|segmentation|Segmentation)).*$', str(f.name)) and re.search(r"[0-9]*.\.nii(.gz)?", str(f.name)) ) ]
        segs = [f for f in Path(path).rglob("*") if re.search(r"[sS]eg(mentation)?\.nii(\.gz)?", str(f.name))]

        return self.zip_cases_with_segs(cases, segs)

    def parse_by_structure(self, path, *args, **kwds):
        img_dir = os.path.join(path, "cases")
        seg_dir = os.path.join(path, "segs")
        cases = glob.glob(os.path.join(img_dir, "*.nii*"))  # TODO: use a proper regex to specifically filter for .nii, .nii.gz and .nrrd
        segs = glob.glob(os.path.join(seg_dir, "*.nii*"))
        
        return self.zip_cases_with_segs(cases, segs, **kwds)


    def zip_cases_with_segs(self, cases, segs, *args, **kwds):
        cases.sort()
        segs.sort()
        if kwds.get("log") in ["Info", "Debug"]:
            print("----cases----")
            for x in cases: print(x)
            print("----segs-----")
            for x in segs: print(x)

        str_segs = [str(s) for s in segs]
        c_names = [os.path.basename(str(c)).split(".") for c in cases]
        s_names = [os.path.basename(str(s)).split(".") for s in segs]

        case_nr = [re.findall(r'\d+', str(c)) for c in c_names]
        seg_nr = [re.findall(r'\d+', str(s)) for s in s_names]

        c_l = [len(case_nr[i]) != 1 for i in range(len(cases))]
        s_l = [len(seg_nr[i]) != 1 for i in range(len(segs))]

        case_nr = [c[0] for c in case_nr]
        seg_nr = [s[0] for s in seg_nr]

        if any(c_l) or any(s_l):
            raise AttributeError("Input file names have multiple numeric values, as a result matching images to segmentations is ambiguous. Please rename your files in a consistent way.")

        seg_dict = {seg_nr[i]: seg for i, seg in enumerate(segs)}
        cases_with_segs = [(cases[i], seg_dict[case_nr[i]]) for i in range(len(cases)) if case_nr[i] in seg_dict.keys()]
        cases_without_segs = [(cases[i], None) for i in range(len(cases)) if case_nr[i] not in seg_dict.keys()]
        print("cases with segs:")
        for c in cases_with_segs:
            print(c)
        print("cases without segs")
        for c in cases_without_segs:
            print(c)

        
        res = [*cases_with_segs, *cases_without_segs]
        return res

def make_seg_args():
    import os
    import json
    json_path = os.path.join(os.environ['OPERATOR_IN_DIR'], 'seg_info.json')
    # case1: seg_info.json exists
    seg_args = {}
    try:
        with open(config_file, 'r') as f:
            config_json = json.load(f)
        config = config_json["seg_args"]
        valid_keys = [
            "INPUT_TYPE", 
            "SINGLE_LABEL_SEG_INFO",
            "CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS",
            "MULTI_LABEL_SEG_INFO_JSON",
            "MULTI_LABEL_SEG_NAME",
            "SERIES_DISCRIPTION",
            "ALGORITHM_NAME",
            "CREATOR_NAME",
            "ALGORITHM_TYPE",
            "SERIES_NUMBER",
            "INSTANCE_NUMBER",
            "SKIP_EMPTY_SLICES",
            "DCMQI_COMMAND",
            "OPERATOR_IMAGE_LIST_INPUT_DIR"]

        for k,v in config.items():
            key = k.upper()
            if key not in valid_keys:
                raise NameError(f"Arguments in 'seg_args.json' is invalid. Valid keys are {valid_keys}")
            os.environ[key] = v
        print("Found args.json in segmentation folder. parameters given by dag will be overwritten.")
    except FileNotFoundError:
        print("No args.json found. Continuing with parameters from dag definition.")



set_args_from_config()

print("Started: 'itkimage2segimage' ")
DCMQI = '/app/dcmqi/bin'


# os.environ['BATCH_NAME'] = 'batch'
# os.environ['OPERATOR_IN_DIR'] = 'input'
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

input_type = os.environ.get('INPUT_TYPE')  # multi_label_seg or single_label_segs
multi_label_seg_name = os.environ.get('MULTI_LABEL_SEG_NAME') if os.environ.get('MULTI_LABEL_SEG_NAME') not in [None, "None", ''] else 'multi-label'  # Name used for multi-label segmentation object, if it will be created
segment_algorithm_name = os.environ.get('ALGORITHM_NAME', 'kaapana')
segment_algorithm_type = os.environ.get('ALGORITHM_TYPE', 'AUTOMATIC')
content_creator_name = os.environ.get('CREATOR_NAME', 'kaapana')
series_description = os.environ.get('SERIES_DISCRIPTION', '')
series_number = os.environ.get('SERIES_NUMBER', '300')
instance_number = os.environ.get('INSTANCE_NUMBER', '1')
skip_empty_slices = True if os.environ.get('SKIP_EMPTY_SLICES', 'false').lower() == "true" else False

get_seg_info_from_file = False
if input_type == 'multi_label_seg':
    multi_label_seg_info_json = os.environ.get('MULTI_LABEL_SEG_INFO_JSON', 'seg_info.json')  # name of json file that contain the parts as follows e.g. {"seg_info": ["spleen", "right@kidney"]}

    if multi_label_seg_info_json == "":
        multi_label_seg_info_json = "seg_info.json"

elif input_type == 'single_label_segs':
    single_label_seg_info = os.environ.get('SINGLE_LABEL_SEG_INFO')  # SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"
    create_multi_label_dcm_from_single_label_segs = os.environ.get('CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS', 'false')  # true or false
    if single_label_seg_info == '':
        raise AssertionError('SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"]}')
    elif single_label_seg_info == 'from_file_name':
        print('Seg info will be taken from file name')
        get_seg_info_from_file = True
    else:
        print(f'Taking {single_label_seg_info} as seg info')
else:
    raise NameError('Input_type must be either multi_label_seg or single_label_segs')


code_lookup_table_path = "code_lookup_table.json"
with open(code_lookup_table_path) as f:
    code_lookup_table = json.load(f)

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

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
        print("skipping!")
        # exit(1)
        continue

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
            print(f"process idx: {idx} - {seg_filepath}")

            seg_filename = os.path.basename(seg_filepath)
            m = re.compile(r'(.*?)(\.nii.gz|\.nii|\.nrrd)').search(seg_filename)
            rootname = m.groups()[-2]

            if get_seg_info_from_file is True:
                single_label_seg_info = rootname

            code_meaning, segmentation_information["SeriesDescription"] = process_seg_info(single_label_seg_info, series_description)
            color = np.round(np.array(cm.get_cmap('gist_ncar', 20)(random.randint(0, 19))[:3])*255).astype(int).tolist()
            segment_attribute = create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning, color)

            if create_multi_label_dcm_from_single_label_segs.lower() == 'true':
                segment_attributes.append([segment_attribute])

            segmentation_information["segmentAttributes"] = [[segment_attribute]]
            meta_data_file = f"{input_image_list_input_dir}/{rootname}.json"

            with open(meta_data_file, "w") as write_file:
                json.dump(segmentation_information, write_file, indent=4, sort_keys=True)

            # Creating dcm_object
            output_dcm_file = f"{element_output_dir}/{rootname}.dcm"

            print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
            print(f"skip_empty_slices: {skip_empty_slices}")
            if skip_empty_slices:
                try:
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
            else:
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
                    print(f'The image seems to have empty slices, we will skip them! This might make the segmentation no usable anymore for MITK. Error: {e.output}')
                    raise AssertionError(f'Something weng wrong while creating the single-label-dcm object {e.output}')

            adding_aetitle(element_input_dir, output_dcm_file, body_part="N/A")
            processed_count += 1

    elif input_type == 'multi_label_seg':
        print("input_type == 'multi_label_seg'")

        json_path = os.path.join(input_image_list_input_dir, multi_label_seg_info_json)
        with open(json_path) as f:
            data = json.load(f)

        print('Loaded seg_info', data)

        if "seg_info" not in data:
            print("Could not find key 'seg_info' in json-file: {}".format(json_path))
            print("Abort!")
            exit(1)

        label_info = data['seg_info']

        body_part = "N/A"
        if "task_body_part" in data:
            body_part = data['task_body_part']

        if "algorithm" in data:
            series_description = "{}-{}".format(segment_algorithm_name, data["algorithm"])

        segment_attributes = [[]]

        label_counts = len(label_info)
        for idx, label in enumerate(label_info):
            label_int = int(label["label_int"])
            single_label_seg_info = label["label_name"]
            print(f"process: {single_label_seg_info}: {label_int}")
            if str(label_int) == "0":
                print("Clear Label -> skipping")
                continue

            code_meaning, segmentation_information["SeriesDescription"] = process_seg_info(single_label_seg_info, series_description)
            color = np.round(np.array(cm.get_cmap('gist_ncar', label_counts)(idx)[:3])*255).astype(int).tolist()
            segment_attribute = create_segment_attribute(segment_algorithm_type, segment_algorithm_name, code_meaning, color, label_name=single_label_seg_info, labelID=label_int)
            segment_attributes[0].append(segment_attribute)

    if input_type == 'multi_label_seg' or create_multi_label_dcm_from_single_label_segs.lower() == 'true':
        _, segmentation_information["SeriesDescription"] = process_seg_info(multi_label_seg_name, series_description)

        segmentation_information["segmentAttributes"] = segment_attributes
        meta_data_file = f"{input_image_list_input_dir}/{multi_label_seg_name.lower()}.json"
        with open(meta_data_file, "w") as write_file:
            print("Writing JSON:: {}".format(meta_data_file))
            json.dump(segmentation_information, write_file, indent=4, sort_keys=True)

        output_dcm_file = f"{element_output_dir}/{multi_label_seg_name.lower()}.dcm"
        print("Output SEG.dcm file:: {}".format(output_dcm_file))
        print("Starting dcmqi-subprocess for: {}".format(output_dcm_file))
        print(f"skip_empty_slices: {skip_empty_slices}")
        if skip_empty_slices:
            try:
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
        else:
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
                print(f'The image seems to have emtpy slices, we will skip them! This might make the segmentation no usable anymore for MITK. Error: {e.output}')
                raise AssertionError(f'Something weng wrong while creating the multi-label-dcm object {e.output}')

        adding_aetitle(element_input_dir, output_dcm_file, body_part=body_part)
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
