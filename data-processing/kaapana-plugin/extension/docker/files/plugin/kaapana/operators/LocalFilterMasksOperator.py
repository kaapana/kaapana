import os
import glob
import json
import datetime
from pathlib import Path
import shutil
import re

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalFilterMasksOperator(KaapanaPythonBaseOperator):
    """
    Operator to filter segmentation label names.

    This operator serves as a segmentation label filter to keep or ignore segmentation label masks.

    **Inputs:**

        * input_operator: Input operator directory containing incoming NIFTI and meta_info JSON files.
        * self.label_filter: Filter indicating the self.mode ('Keep' or 'Ignore') and the label_names to keep or ignore. E.g. 'Keep: liver' or 'Ignore: spleen,liver'

    **Outputs**

        * modified metainfo.json with kept/ignored label names
        * copies kept/not ignored NIFTI files to output dir

    """

    def remove_special_characters(self, input_string):
        # Convert the string to lowercase
        input_string = input_string.lower()
        # Define the regex pattern
        pattern = re.compile("[^a-z0-9.]")
        # Use sub() method to replace matched characters with underscores
        result = re.sub(pattern, "", input_string)

        return result

    def set_label_filters(self, conf):
        """
        Parse the value of self.label_filter_key and assign to self.label_filter
        """
        self.label_filter = []
        # check whether self.label_filter_key is set
        if self.label_filter_key in conf["form_data"]:
            val = conf["form_data"][self.label_filter_key]
            if conf["form_data"][self.label_filter_key]:
                if ":" in val:
                    self.mode = val.split(":")[0]
                    self.label_filter = val.split(":")[1].split(",")
                else:
                    print("### ERROR ###")
                    print("#")
                    print(f"# {self.label_filter_key} IS NOT SET CORRECTLY")
                    print(
                        "# CORRECT FORMAT: e.g. 'Keep: liver' or 'Ignore: spleen,liver'"
                    )
                    print("#")
                    exit(1)
            else:
                print("### WARNING ###")
                print("#")
                print(f"# NO {self.label_filter_key} SET.")
                print("# Finish process without processing any data.")
                print("#")
                self.mode = ""
        else:
            print("### WARNING ###")
            print("#")
            print("# NO self.label_filter SET.")
            print("# Finish process without processing any data.")
            print("#")
            self.mode = ""

        print(f"{self.label_filter=}, {self.mode=}")
        return

    def start(self, ds, **kwargs):
        print("Starting module LocalFilterMasksOperator...")
        print(kwargs)

        skip_operator = False

        # load user input's label renaming look-up table
        conf = kwargs["dag_run"].conf
        print("CONF:")
        print(conf["form_data"])

        self.set_label_filters(conf)

        self.mode = self.remove_special_characters(self.mode)
        self.label_filter = [
            self.remove_special_characters(label) for label in self.label_filter
        ]
        print("#")
        print(f"GIVEN self.mode: {self.mode}")
        print(f"GIVEN self.label_filter: {self.label_filter}")
        print("#")

        # define input dirs
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]

        # iterate over batches
        for batch_element_dir in batch_dirs:
            # define batch-wise input and output dirs

            # get meta_info json
            batch_el_json_files = sorted(
                glob.glob(
                    os.path.join(
                        batch_element_dir, self.operator_in_dir, "**", "*.json*"
                    ),
                    recursive=True,
                )
            )
            # get metainfo json of incoming dcm_seg object
            print(f"{batch_el_json_files=}")
            for batch_el_metainfo_json_file in batch_el_json_files:
                with open(batch_el_metainfo_json_file) as data_file:
                    incoming_metainfo = json.load(data_file)
            print("# INCOMING DICOMSEG METAINFO: ")
            print(f"Filename: {batch_el_metainfo_json_file=}")
            print(json.dumps(incoming_metainfo, indent=4))
            print(f"{type(incoming_metainfo)=}")

            if self.mode == "keep" or self.mode == "ignore":
                # output dir for meta_info json
                metainfo_output_path = batch_el_json_files[0].replace(
                    self.operator_in_dir, self.operator_out_dir
                )
                # make output directory
                Path(os.path.dirname(metainfo_output_path)).mkdir(
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

            if self.mode == "keep":
                num_kept_labels = 0

                # iterate over niftis
                for nifti_fname in nifti_files:
                    # check if current nifti_fname is of ignored label_name; if yes, don't copy to out_dir
                    copy = any(
                        label_name in self.remove_special_characters(nifti_fname)
                        for label_name in self.label_filter
                    )
                    if copy:
                        src_path, dest_path = nifti_fname, os.path.join(
                            os.path.dirname(metainfo_output_path),
                            os.path.basename(nifti_fname),
                        )
                        shutil.copy(src_path, dest_path)
                        num_kept_labels += 1

                # iterate over label_names in self.label_filter
                temp_incoming_metainfo_segment_attributes = []
                for label_name in self.label_filter:
                    # modify meta_info JSON according to self.label_filter
                    for segment_attribute in incoming_metainfo["segmentAttributes"]:
                        if label_name in self.remove_special_characters(
                            json.dumps(segment_attribute)
                        ):
                            temp_incoming_metainfo_segment_attributes.append(
                                segment_attribute
                            )
                incoming_metainfo[
                    "segmentAttributes"
                ] = temp_incoming_metainfo_segment_attributes
                # write incoming_metainfo to output_dir
                with open(metainfo_output_path, "w", encoding="utf-8") as jsonData:
                    json.dump(incoming_metainfo, jsonData, indent=4, sort_keys=True)

                print("#")
                print(
                    f"# DONE: I kept {num_kept_labels} out of {len(nifti_files)} labels."
                )
                print("#")

            elif self.mode == "ignore":
                num_ignored_labels = 0

                # iterate over niftis
                for nifti_fname in nifti_files:
                    # check if current nifti_fname is of ignored label_name; if yes, don't copy to out_dir
                    copy = all(
                        label_name not in self.remove_special_characters(nifti_fname)
                        for label_name in self.label_filter
                    )
                    if copy:
                        src_path, dest_path = nifti_fname, os.path.join(
                            os.path.dirname(metainfo_output_path),
                            os.path.basename(nifti_fname),
                        )
                        shutil.copy(src_path, dest_path)
                        num_ignored_labels += 1

                # iterate over label_names in self.label_filter
                for label_name in self.label_filter:
                    # modify meta_info JSON according to self.label_filter
                    temp_incoming_metainfo_segment_attributes = []
                    for segment_attribute in incoming_metainfo["segmentAttributes"]:
                        if label_name not in self.remove_special_characters(
                            json.dumps(segment_attribute)
                        ):
                            temp_incoming_metainfo_segment_attributes.append(
                                segment_attribute
                            )
                    incoming_metainfo[
                        "segmentAttributes"
                    ] = temp_incoming_metainfo_segment_attributes
                    # write incoming_metainfo to output_dir
                    with open(metainfo_output_path, "w", encoding="utf-8") as jsonData:
                        json.dump(incoming_metainfo, jsonData, indent=4, sort_keys=True)

                print("#")
                print(
                    f"# DONE: I ignored {num_ignored_labels} out of {len(nifti_files)} labels."
                )
                print("#")

            else:
                # just copy everything from operator_in_dir to operator_out_dir
                shutil.copytree(
                    os.path.join(batch_element_dir, self.operator_in_dir),
                    os.path.join(batch_element_dir, self.operator_out_dir),
                )

                print("#")
                print(
                    f"# DONE: I just copied all files belonging to the  {len(nifti_files)} labels to the output_dir: {self.operator_out_dir}."
                )
                print("#")
                skip_operator = True

        if skip_operator:
            # ti = kwargs['ti']
            # ti.state = 'skipped'
            self.skip_on_exit_code = 1

    def __init__(
        self,
        dag,
        name="filter-seg-label-masks",
        label_filter_key="label_filter",
        **kwargs,
    ):
        self.label_filter_key = label_filter_key
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
