import os
import glob
import json
import datetime
from pathlib import Path
import shutil

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalModifySegLabelNamesOperator(KaapanaPythonBaseOperator):
    """
    # Description

    **Inputs:**

        * # sth

    **Outputs**

        * # sth

    """

    def replace_label_name_in_dict(metadata_dict, curr_label, new_label):
        if isinstance(metadata_dict, dict):
            for key, value in metadata_dict.items():
                if isinstance(value, str):
                    metadata_dict[key] = value.replace(curr_label, new_label)
                    # return metadata_dict
                else:
                    replace_label_name_in_dict(value)
        elif isinstance(metadata_dict, list):
            for item in metadata_dict:
                replace_label_name_in_dict(item)

    def start(self, ds, **kwargs):
        print("Starting module LocalModifySegLabelNamesOperator...")
        print(kwargs)

        # define input dirs
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))]

        # load user input's label renaming look-up table
        conf = kwargs["dag_run"].conf
        print("CONF:")
        print(conf["form_data"])
        if ("old_labels" in conf["form_data"]) and ("new_labels" in conf["form_data"]):
            old_label_names = (
                conf["form_data"]["old_labels"].lower().replace(" ", "").split(",")
            )
            new_label_names = (
                conf["form_data"]["new_labels"].lower().replace(" ", "").split(",")
            )
        else:
            print("### ERROR ###")
            print("#")
            print("# No OLD_LABELS or NEW_LABELS defined in workflow_form.")
            print("#")
            exit(1)
        print(f"# OLD LABELS: {old_label_names}")
        print(f"# NEW LABELS: {new_label_names}")

        # instantiate output json
        new_metadata_json = {}
        new_metadata_json["seg_info"] = []

        # iterate over batches
        for batch_element_dir in batch_dirs:
            # define batch-wise input and output dirs        )
            batch_el_json_files = sorted(
                glob.glob(
                    os.path.join(
                        batch_element_dir, self.operator_in_dir, "**", "*.json*"
                    ),
                    recursive=True,
                )
            )
            # output dir
            json_output_path = os.path.join(
                run_dir,
                self.batch_name,
                batch_element_dir,
                self.operator_out_dir,
                "seg_info.json",
            )
            # make output directory
            Path(os.path.dirname(json_output_path)).mkdir(parents=True, exist_ok=True)

            # get metadata json of incoming dcm_seg object
            for batch_el_json_file in batch_el_json_files:
                with open(batch_el_json_file) as data_file:
                    incoming_dcm_metadata = json.load(data_file)
            print("# INCOMING DCM_SEG METADATA: ")
            print(f"Filename: {batch_el_json_file=}")
            print(json.dumps(incoming_dcm_metadata, indent=4))
            print(f"{type(incoming_dcm_metadata)=}")

            # add "Clear Label" entry
            if self.clear_label_as_zero:
                segment_dict = {}
                segment_dict["label_name"] = "Clear Label"
                segment_dict["label_int"] = "0"
                new_metadata_json["seg_info"].append(segment_dict)

            # iterate over "segmentAttributes" in incoming_dcm_metadata
            if "segmentAttributes" in incoming_dcm_metadata:
                for segment in incoming_dcm_metadata["segmentAttributes"]:
                    print("# SEGMENT: ")
                    print(json.dumps(segment, indent=4))

                    # extract current segmentation_label_name and labelID
                    curr_segmentation_label_name = segment[0]["SegmentLabel"]
                    segmentation_label_id = segment[0]["labelID"]
                    print(
                        f"# CURRENT SEGMENTATION LABEL NAME: {curr_segmentation_label_name}"
                    )
                    print(f"# CURRENT SEGMENTATION LABEL ID: {segmentation_label_id}")

                    # find new segmentation_label_name based on current (aka. old) segmentation_label_name
                    # check if curr_segmentation_label_name is in old_label_names list
                    if curr_segmentation_label_name in old_label_names:
                        new_segmentation_label_name = new_label_names[
                            old_label_names.index(curr_segmentation_label_name)
                        ]
                        print("#")
                        print(
                            f"# FOUND CURRENT SEGMENTATION LABEL NAME = {curr_segmentation_label_name} IN LIST OF OLD LABEL NAMES."
                        )
                        print(
                            f"# NEW SEGMENTATION LABEL NAME: {new_segmentation_label_name}"
                        )
                        segmentation_label_name = new_segmentation_label_name

                        # replace curr_segmentation_label_name with new_segmentation_label_name in incoming dcm_seg metadata
                        incoming_dcm_metadata = json.loads(
                            json.dumps(incoming_dcm_metadata).replace(
                                curr_segmentation_label_name, segmentation_label_name
                            )
                        )
                    else:
                        print(
                            f"# COULD NOT FIND CURRENT SEGMENTATION LABEL NAME = {curr_segmentation_label_name} IN LIST OF OLD LABEL NAMES = {old_label_names}."
                        )
                        segmentation_label_name = curr_segmentation_label_name

                    # compose dict
                    segment_dict = {}
                    segment_dict["label_int"] = f"{segmentation_label_id}"
                    segment_dict["label_name"] = f"{segmentation_label_name}"

                    # append to output json
                    new_metadata_json["seg_info"].append(segment_dict)

            print("# MODIFIED SEG INFO:")
            print(json.dumps(new_metadata_json, indent=4))
            # write to file in output dir
            with open(json_output_path, "w", encoding="utf-8") as jsonData:
                json.dump(new_metadata_json, jsonData, indent=4, sort_keys=True)
            # copy output json also to operator_in_dir bc subsequential nrrd2dcmseg operator needs seg_info.json there
            second_json_output_path = os.path.join(
                run_dir,
                self.batch_name,
                batch_element_dir,
                self.operator_in_dir,
                "seg_info.json",
            )
            shutil.copyfile(json_output_path, second_json_output_path)

            print("# MODIFIED DCM META DATA:")
            print(json.dumps(incoming_dcm_metadata, indent=4))
            # write to file in output dir
            with open(batch_el_json_file, "w", encoding="utf-8") as jsonData:
                json.dump(incoming_dcm_metadata, jsonData, indent=4, sort_keys=True)
            # copy output json also to operator_in_dir bc subsequential nrrd2dcmseg operator needs seg_info.json there
            # second_json_output_path = os.path.join(
            #     run_dir, self.batch_name, batch_element_dir, self.operator_in_dir, batch_el_json_file
            # )
            # shutil.copyfile(json_output_path, second_json_output_path)

    def __init__(
        self, dag, name="rename-seg-label-names", clear_label_as_zero=False, **kwargs
    ):
        """ """
        self.clear_label_as_zero = clear_label_as_zero

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
