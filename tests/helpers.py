import json
import shutil
from deepdiff import DeepDiff
from pprint import pprint

import pydicom


def save_json(json_dict, json_file_path):
    with open(json_file_path, "w", encoding="utf-8") as fp:
        json.dump(json_dict, fp, indent=4, sort_keys=True)


def copy_to_tmp_directory(src_file, tmp_dir, version):
    dst_file = tmp_dir / f"{version}_{src_file.name}"
    shutil.copy2(src_file, dst_file)
    return dst_file


def print_all_meta_information(dcm_file_path):
    ds = pydicom.dcmread(dcm_file_path, force=True)

    # Print all meta information
    print("All Meta Information:")
    for elem in ds.file_meta:
        tag = elem.tag
        vr = elem.VR
        value = elem.value
        print(f"Tag: {tag} | VR: {vr} | Value: {value}")


def compare_jsons(v1_dir, v2_dir):
    
    for v1_file, v2_file in zip(sorted(v1_dir.glob("*")), sorted(v2_dir.glob("*"))):
        if v1_file.name != v2_file.name:
            print("Mismatch")
            continue
        with open(v1_file, 'r', encoding="utf-8") as v1, open(v2_file, 'r', encoding="utf-8") as v2:
            json1 = json.load(v1)
            json2 = json.load(v2)

            diff = DeepDiff(json1, json2, ignore_order=True,
                            ignore_numeric_type_changes=True, significant_digits=5,
                            exclude_paths=["root['00000000 TimestampArrivedHour_integer']",
                                           "root['00000000 TimestampArrived_datetime']",
                                           "root['00080005 SpecificCharacterSet_keyword']",
                                           "root['00000000 TimeTagUsed_keyword']",
                                           "root['00104000 PatientComments_keyword']"
                                           ]).pretty()

            if diff:
                print(f"Old: {v1_file}")
                print(f"New: {v2_file}")

                pprint(diff, indent=2)

            else:
                print(f"No difference in {v1_file}")
