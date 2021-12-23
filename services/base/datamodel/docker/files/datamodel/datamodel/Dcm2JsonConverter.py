import datetime
from calendar import _localized_day

import pydicom
import os
import base64
from typing import Dict


class Dcm2JsonConverter:
    def __init__(self, delete_private_tags: bool) -> dict:
        self.format_time = "%H:%M:%S.%f"
        self.format_date = "%Y-%m-%d"
        self.format_date_time = "%Y-%m-%d %H:%M:%S.%f"
        #TODO change paths!
        self.json_dir = "/tmp"
        cwd = os.path.dirname(__file__)
        self.dict_path = os.path.join(cwd, "scripts/dicom_tag_dict.json")
        self.delete_private_tags = delete_private_tags

    def clean(self, dcm_dict):
        result = {}
        for (tag, data) in dcm_dict.items():
            vr = data["vr"]
            value = None
            if "InlineBinary" in data:
                # http://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_F.2.7.html
                #value = base64.b64encode(data["InlineBinary"].encode('utf-8'))
                result[tag] = {
                    "vr": vr,
                    "InlineBinary": data["InlineBinary"],
                    "QueryValue": data["InlineBinary"]
                }
                continue
            elif "Value" in data:
                value = data["Value"]
            else:
                print(f"Don't know how to read value for {data}")

            if not value or len(value) == 0:
                print(f"Warning: empty value for {tag}")
                continue
            try:
                if vr == "DS":
                    cleaned_val = float(value[0])
                elif vr == "SQ":
                    cleaned_val = [self.clean(x) for x in value]
                elif vr in ["AE", "LO", "LT", "UI", "CS", "SH", "UN"]:
                    cleaned_val = value[0]
                elif vr in ["IS", "US", "UL"]:
                    cleaned_val = int(value[0])
                elif vr == "AS":
                    number = int(value[0][:3])
                    span = value[0][3]
                    if span == "D":
                        cleaned_val = number
                    elif span == "W":
                        cleaned_val = number * 7
                    elif span == "M":
                        # Be warned: this might not be exact!
                        cleaned_val = number * 30
                    elif span == "Y":
                        # Be warned: this might not be exact!
                        cleaned_val = number * 365
                elif vr == "DA":
                        #year = int(value[0][:4])
                        #month = int(value[0][4:6])
                        #day = int(value[0][6:8])
                        #cleaned_val = datetime.date(year=year, month=month, day=day)
                        # sqlalchemy.exc.StatementError: (builtins.TypeError) Object of type date is not JSON serializable
                        cleaned_val = value[0]
                        vtest = int(value[0])
                        print(vtest)
                else:
                    print(f"Warning: unkown VR {vr}")
                    cleaned_val = value
            except Exception as e:
                print(f"Error {e}")
                cleaned_val = value
            result[tag] = {
                "vr": vr,
                "Value": value,
                "QueryValue": cleaned_val
            }
        return result

    def start(self, dcm_file: str) -> Dict:
        print("Starting moule dcm2json converter...")
        ds = pydicom.dcmread(dcm_file)
        dcm_file_dict = ds.to_json_dict()
        cleaned = self.clean(dcm_file_dict)
        return cleaned