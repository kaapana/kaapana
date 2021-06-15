# -*- coding: utf-8 -*-

import subprocess
import os
import fnmatch
import json
import yaml
from pathlib import Path
import shutil
import pathlib
from datetime import datetime
from dateutil import parser
import pytz
import traceback
import logging
import glob
from shutil import copyfile, rmtree
import errno
import re

import pydicom


from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.Dcm2MetaJsonConverter import Dcm2MetaJsonConverter


class LocalDcm2JsonOperator(KaapanaPythonBaseOperator):

    @staticmethod
    def get_manual_tags(dcm_file_path):
        label_list_id = "segmentation_labels_list_keyword"
        def _add_manual_tag(de, manual_tags):
            k = f'{str(de.tag).replace("(", "").replace(", ", "").replace(")", "")} {de.name}_keyword'
            if de.value not in manual_tags[label_list_id]:
                manual_tags[label_list_id].append(de.value)
            if k in manual_tags:
                manual_tags[k].append(de.value)
                manual_tags[k] = list(set(manual_tags[k]))
            else:
                manual_tags.update({k: [de.value]})

        dicom = pydicom.dcmread(dcm_file_path)
        manual_tags = {
            label_list_id: []
        }
        if (0x0062, 0x0002) in dicom:
            for seg_seq in dicom[0x0062, 0x0002]:
                if (0x008, 0x2218) in seg_seq:
                    for anatomic_reg_seq in seg_seq[0x008, 0x2218]:
                        if (0x0008, 0x0104) in anatomic_reg_seq:
                            de = anatomic_reg_seq[0x0008, 0x0104]
                            _add_manual_tag(de, manual_tags)

                if (0x0062, 0x0005) in seg_seq:
                    de = seg_seq[0x0062, 0x0005]
                    _add_manual_tag(de, manual_tags)
                if (0x0062, 0x0020) in seg_seq:
                    de = seg_seq[0x0062, 0x0020]
                    _add_manual_tag(de, manual_tags)

        manual_tags[label_list_id] = ','.join(map(str, sorted(manual_tags[label_list_id]))) 
        return manual_tags


    @cache_operator_output
    def start(self, ds, **kwargs):
        print("Starting moule dcm2json...")
        print(kwargs)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        with open(self.dict_path, encoding='utf-8') as dict_data:
            self.dictionary = json.load(dict_data)

        for batch_element_dir in batch_folder:
            dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))

            if len(dcm_files) == 0:
                print("No dicom file found!")
                exit(1)

            print('length', len(dcm_files))
            for dcm_file_path in dcm_files:

                print(("Extracting metadata: %s" % dcm_file_path))

                target_dir = os.path.join(batch_element_dir, self.operator_out_dir)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                json_file_path = os.path.join(target_dir, "{}.json".format(os.path.basename(batch_element_dir)))

                if self.delete_private_tags:
                    print("Deleting private tags!")
                    command = "%s --no-backup --ignore-missing-tags --erase-all \"(0014,3080)\" --erase-all \"(7FE0,0008)\" --erase-all \"(7FE0,0009)\" --erase-all \"(7FE0,0010)\" %s;" % (
                        self.dcmodify_path, dcm_file_path)
                else:
                    command = "%s --no-backup --ignore-missing-tags --erase-all \"(0014,3080)\" --erase-all \"(7FE0,0008)\" --erase-all \"(7FE0,0009)\" --erase-all \"(7FE0,0010)\" %s;" % (
                        self.dcmodify_path, dcm_file_path)
                # (0014,3080) Bad Pixel Image
                # (7FE0,0008) Float Pixel Data
                # (7FE0,0009) Double Float Pixel Data
                # (7FE0,0010) Pixel Data
                ret = subprocess.call([command], shell=True)
                if ret != 0:
                    print("Something went wrong with dcmodify...")
                    exit(1)
                self.executeDcm2Json(dcm_file_path, json_file_path)

                with open(json_file_path, "r") as fp:
                    dcm_json_dict = json.load(fp)

                meta_json_dict = self.converter.dcmJson2metaJson(dcm_json_dict)

                manual_tags = LocalDcm2JsonOperator.get_manual_tags(dcm_file_path)
                json_dict.update(manual_tags)

                with open(json_file_path, "w", encoding='utf-8') as jsonData:
                    json.dump(meta_json_dict, jsonData, indent=4, sort_keys=True, ensure_ascii=True)

                # shutil.rmtree(self.temp_dir)

                if self.bulk == False:
                    break

    def executeDcm2Json(self, inputDcm, outputJson):
        """
        Executes a conversion service

        program -- path to the service
        arguments -- the arguments for the service
        """

        command = self.dcm2json_path + " " + \
            self.withAppostroph(inputDcm) + " " + \
            self.withAppostroph(outputJson)
        print(("Executing: " + command))
        ret = subprocess.call(command, shell=True)
        if ret != 0:
            print("Something went wrong with dcm2json...")
            exit(1)
        return

    def withAppostroph(self, content):
        return "\"" + content + "\""

  
    def __init__(self,
                 dag,
                 exit_on_error=False,
                 delete_private_tags=True,
                 bulk=False,
                 *args, **kwargs):

        self.dcmodify_path = 'dcmodify'
        self.dcm2json_path = 'dcm2json'
        self.converter = Dcm2MetaJsonConverter(
            format_time="%H:%M:%S.%f",
            format_date="%Y-%m-%d",
            format_date_time="%Y-%m-%d %H:%M:%S.%f",
            exception_on_error=exit_on_error
        )

        self.bulk = bulk
        self.exit_on_error = exit_on_error
        self.delete_private_tags = delete_private_tags

        os.environ["PYTHONIOENCODING"] = "utf-8"
        if 'DCMDICTPATH' in os.environ and 'DICT_PATH' in os.environ:
            self.dcmdictpath = os.getenv('DCMDICTPATH')
            self.dict_path = os.getenv('DICT_PATH')
        else:
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("DCMDICTPATH or DICT_PATH ENV NOT FOUND!")
            print("dcmdictpath: {}".format(os.getenv('DCMDICTPATH')))
            print("dict_path: {}".format(os.getenv('DICT_PATH')))
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            exit(1)

        super().__init__(
            dag,
            name="dcm2json",
            python_callable=self.start,
            ram_mem_mb=10,
            *args, **kwargs
        )
