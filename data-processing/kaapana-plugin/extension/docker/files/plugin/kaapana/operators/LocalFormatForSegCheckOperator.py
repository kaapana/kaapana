import os
import glob
import json
import datetime
from pathlib import Path
import shutil
import re

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalFormatForSegCheckOperator(KaapanaPythonBaseOperator):
    """ """

    def remove_special_characters(self, input_string):
        # Convert the string to lowercase
        input_string = input_string.lower()
        # Define the regex pattern
        pattern = re.compile("[^a-z0-9.]")
        # Use sub() method to replace matched characters with underscores
        result = re.sub(pattern, "", input_string)

        return result

    def start(self, ds, **kwargs):
        print("Starting module LocalFormatForSegCheckOperator...")
        print(kwargs)

        # load user input's label renaming look-up table
        conf = kwargs["dag_run"].conf
        print("CONF:")
        print(conf["form_data"])

        # define input dirs
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]

        # iterate over batches
        for batch_element_dir in batch_dirs:
            # define batch-wise input and output dirs

            # get seg_info json
            batch_el_json_files = sorted(
                glob.glob(
                    os.path.join(
                        batch_element_dir, self.operator_in_dir, "**", "*.json*"
                    ),
                    recursive=True,
                )
            )
            # get seg_info json
            print(f"{batch_el_json_files=}")
            for batch_el_metainfo_json_file in batch_el_json_files:
                with open(batch_el_metainfo_json_file) as data_file:
                    incoming_seginfo = json.load(data_file)
            print("# INCOMING DICOMSEG SEGINFO:")
            print(f"Filename: {batch_el_metainfo_json_file=}")
            print(json.dumps(incoming_seginfo, indent=4))
            print(f"{type(incoming_seginfo)=}")

            # output dir for seg_info json
            seginfo_output_path = batch_el_json_files[0].replace(
                self.operator_in_dir, self.operator_out_dir
            )
            seginfo_output_path = os.path.join(
                os.path.dirname(seginfo_output_path), "seg_info-1.json"
            )
            # make output directory
            Path(os.path.dirname(seginfo_output_path)).mkdir(
                parents=True, exist_ok=True
            )

            # NIFTI files
            # get all nifti files of current batch element
            nifti_files = sorted(
                glob.glob(
                    os.path.join(
                        batch_element_dir, self.operator_in_dir, "**", "*.nii.gz"
                    ),
                    recursive=True,
                )
            )

            # rename nifti files and save to out_dir
            for nifti_file in nifti_files:
                dest = os.path.join(
                    os.path.dirname(nifti_file).replace(
                        self.operator_in_dir, self.operator_out_dir
                    ),
                    "imagine_a_uid--1.nii.gz",
                )
                shutil.copyfile(nifti_file, dest)

            # Iterate through seg_info list and update label_int
            for i, item in enumerate(incoming_seginfo["seg_info"]):
                item["label_int"] = i + 1
            print(json.dumps(incoming_seginfo, indent=4))

            # write incoming_seginfo to output_dir
            with open(seginfo_output_path, "w", encoding="utf-8") as jsonData:
                json.dump(incoming_seginfo, jsonData, indent=4, sort_keys=True)

    def __init__(
        self,
        dag,
        name="format-for-seg-check",
        **kwargs,
    ):
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
