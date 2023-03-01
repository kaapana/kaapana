import os
import glob
import json
import os
import subprocess

processed_count = 0
DCMQI = '/kaapana/app/dcmqi/bin'


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

    dcmseg_file.add_new([0x012, 0x020], 'LO', aetitle)  # Clinical Trial Protocol ID
    dcmseg_file.save_as(output_dcm_file)

# Example: https://github.com/QIICR/dcmqi/blob/master/doc/examples/seg-example.json
# SegmentedPropertyCategoryCodeSequence: Sequence defining the general category of the property the segment represents: https://dicom.innolitics.com/ciods/rt-structure-set/rt-roi-observations/30060080/00620003
# SegmentedPropertyTypeCodeSequence: https://dicom.innolitics.com/ciods/segmentation/segmentation-image/00620002/0062000f
# Note
# "Property" is used in the sense of meaning "what the segmented voxels represent", whether it be a physical or biological object, be real or conceptual, having spatial, temporal or functional extent or not. I.e., it is what the segment "is" (as opposed to some feature, attribute, quality, or characteristic of it, like color or shape or size).
# Only a single Item shall be included in this Sequence.
# http://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html#chapter_L

def set_args_file(batch_element_dir):

    config_file = '/data/conf/conf.json'
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            seg_args = config['seg_args']


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

        for k,v in seg_args.items():
            key = k.upper()
            if key not in valid_keys:
                raise NameError(f"Arguments in 'seg_args.json' is invalid. Valid keys are {valid_keys}")
            os.environ[key] = v
        print("Found args.json in segmentation folder. parameters given by dag will be overwritten.")
    except FileNotFoundError:
        print("No args.json found. Continuing with parameters from dag definition.")

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

set_args_file(batch_folders[0])


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
    seg_filter = None

if output_type not in ['nrrd', 'mhd', 'mha', 'nii', 'nii.gz', 'nifti', 'hdr', 'img']:
    raise AssertionError('Output type must be <nrrd|mhd|mha|nii|nii.gz|nifti|hdr|img>')

if output_type == "nii.gz":
    output_type_dcmqi = "nii"
else:
    output_type_dcmqi = output_type

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

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
            segment_label = segment_info['SegmentLabel'].lower()
            print(f"SEG-INFO: {segment_label} -> Label: {segment_info['labelID']}")
            if seg_filter is None or segment_label.lower().replace(","," ").replace("  "," ") in seg_filter:
                segment_label = segment_label.replace("/", "++")
                os.rename(os.path.join(element_output_dir, f'{json_output}-{segment_info["labelID"]}.{output_type}'),
                          os.path.join(element_output_dir, f'{json_output}--{segment_info["labelID"]}--{segment_label}.{output_type}'))
            else:
                to_remove_indexes.append(idx)
                os.remove(os.path.join(element_output_dir, f'{json_output}-{segment_info["labelID"]}.{output_type}'))

        # Updating meta-data-json
        for idx in sorted(to_remove_indexes, reverse=True):
            del meta_data['segmentAttributes'][idx]

        with open(meta_data_file, "w") as write_file:
            json.dump(meta_data, write_file, indent=4, sort_keys=True)
            # print("Overwriting JSON: {}".format(meta_data_file))
        # print(json.dumps(meta_data, indent=4, sort_keys=True))

        if seg_filter != None and seg_filter != "":
            len_output_files = len(sorted(glob.glob(os.path.join(element_output_dir, f"*{output_type_dcmqi}*"), recursive=False)))
            if len_output_files != len(seg_filter):
                print(f"Found {len_output_files} files -> expected {len(seg_filter)}!")
                print(f"Filter: {seg_filter}")

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
