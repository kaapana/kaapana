import os
import glob
import json
import datetime
from pathlib import Path
import shutil

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalModifySegLabelNamesOperator(KaapanaPythonBaseOperator):
    """
    Operator to rename segmentation label names.

    This operator takes as input a list of old and to-be-replaced label names, a list of new label names.
    These label names are modified in the incoming_seg_info and in the incoming_metainfo JSON files which are loaded via the two defined input_operator directories.

    **Inputs:**

        * input_operator: Input operator directory to load incoming_seg_info JSON file from it.
        * metainfo_input_operator:  Input operator directory to load incoming_metainfo JSON file from it.
        * old_label_names: list of old label names which should be replaced; input via UI form; same order necessary as in new_label_names, e.g. [aorta, liver]
        * new_label_names: list of new label names which should replace old label names; input via UI form; same order necessary as in old_label_names, e.g. [cool_aorta, oliver]

    **Outputs**

        * modified seg_info.json with renamed label names; stored in operator out_dir and in operator_in_dir (necessary for nrrd2dcmseg operator which is (mostly) used afterwards)
        * modified metainfo.json with renamed label names; stored in operator out_dir and in operator_in_dir (necessary for nrrd2dcmseg operator which is (mostly) used afterwards)

    """

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
            # define batch-wise input and output dirs
            batch_el_json_files = sorted(
                glob.glob(
                    os.path.join(
                        batch_element_dir, self.operator_in_dir, "**", "*.json*"
                    ),
                    recursive=True,
                )
            )
            print(f"{self.metainfo_input_operator.name=}")
            batch_el_metainfo_json_files = sorted(
                glob.glob(
                    os.path.join(
                        batch_element_dir,
                        self.metainfo_input_operator.name,
                        "**",
                        "*.json*",
                    ),
                    recursive=True,
                )
            )
            # output dir
            seg_info_output_path = os.path.join(
                run_dir,
                self.batch_name,
                batch_element_dir,
                self.operator_out_dir,
                "seg_info.json",
            )
            # make output directory
            Path(os.path.dirname(seg_info_output_path)).mkdir(
                parents=True, exist_ok=True
            )
            # output dir
            metainfo_output_path = os.path.join(
                run_dir,
                self.batch_name,
                batch_element_dir,
                self.operator_out_dir,
                f"{self.name}.json",
            )
            # make output directory
            Path(os.path.dirname(metainfo_output_path)).mkdir(
                parents=True, exist_ok=True
            )

            # get seg_info json of modified dcm_seg object
            for batch_el_json_file in batch_el_json_files:
                with open(batch_el_json_file) as data_file:
                    incoming_seg_info = json.load(data_file)
            print("# INCOMING SEG INFO: ")
            print(f"Filename: {batch_el_json_file=}")
            print(json.dumps(incoming_seg_info, indent=4))
            print(f"{type(incoming_seg_info)=}")

            # get metainfo json of incoming dcm_seg object
            for batch_el_metainfo_json_file in batch_el_metainfo_json_files:
                with open(batch_el_metainfo_json_file) as data_file:
                    incoming_metainfo = json.load(data_file)
            print("# INCOMING DICOMSEG METAINFO: ")
            print(f"Filename: {batch_el_metainfo_json_file=}")
            print(json.dumps(incoming_metainfo, indent=4))
            print(f"{type(incoming_metainfo)=}")

            # iterate over old_label_names and replace them by corresponding new_label_names in incoming_seg_info
            for old_label_name in old_label_names:
                # find corresponding new label name
                new_label_name = new_label_names[old_label_names.index(old_label_name)]
                print("#")
                print("#")
                print(
                    f"# FOUND OLD SEGMENTATION LABEL NAME = {old_label_name} IN LIST OF OLD LABEL NAMES."
                )
                print(f"# REPLACE BY NEW SEGMENTATION LABEL NAME: {new_label_name}")
                print("#")
                print("#")

                # check if old_label_name is even part of incoming_seg_info or incoming_metainfo
                if (
                    old_label_name in json.dumps(incoming_seg_info).lower()
                    or old_label_name in json.dumps(incoming_metainfo).lower()
                ):
                    print("#")
                    print("#")
                    print(
                        f"# FOUND OLD SEGMENTATION LABEL NAME = {old_label_name} IN INCOMING_SEG_INFO OR INCOMING_METAINFO."
                    )
                    print("#")
                    print("#")

                    # replace old_label_name with new_label_name in incoming_seg_info
                    incoming_seg_info = json.loads(
                        json.dumps(incoming_seg_info)
                        .lower()
                        .replace(old_label_name, new_label_name)
                    )

                    # replace old_label_name with new_label_name in incoming_metainfo
                    incoming_metainfo = json.loads(
                        json.dumps(incoming_metainfo)
                        .lower()
                        .replace(old_label_name, new_label_name)
                    )
                else:
                    print("#")
                    print("#")
                    print(
                        f"# COULD NOT FIND OLD SEGMENTATION LABEL NAME = {old_label_name} IN INCOMING_SEG_INFO OR INCOMING_METAINFO. ==> SKIP BATCH ELEMENT!"
                    )
                    print("#")
                    print("#")

            # restructure incoming_metainfo such that "segmentAttributes" is in the right format to support multi_label itkimage2dcmimage functionalities
            segmentAttributes = incoming_metainfo["segmentAttributes".lower()]
            if (
                len(segmentAttributes) > 1
                and sum(isinstance(element, list) for element in segmentAttributes) > 1
            ):
                # segmentAttributes is a list of multiple lists ==> restructuring necessary
                print("#")
                print("#")
                print("RESTRUCTURING OF segmentAttributes NECESSARY!")
                print("#")
                print("#")

                # instantiate new segmentAttributes list
                new_segmentAttributes = []

                # retrieve single segmentAttribute dicts
                for segmentAttribute_list in segmentAttributes:
                    segmentAttribute = segmentAttribute_list[0]

                    # append single segmentAttribute dicts to new_segmentAttributes list
                    new_segmentAttributes.append(segmentAttribute)

                # delete wrongly structured segmentAttributes from incoming_metainfo
                del incoming_metainfo["segmentAttributes".lower()]

                # add new and correctly structured segmentAttributes to incoming_metainfo
                incoming_metainfo["segmentAttributes".lower()] = [new_segmentAttributes]

            print("#")
            print("#")
            print("# MODIFIED SEG INFO:")
            print(json.dumps(incoming_seg_info, indent=4))
            print("#")
            print("#")
            print("#")
            print("#")
            print("# MODIFIED METAINFO:")
            print(json.dumps(incoming_metainfo, indent=4))

            # save incoming_seg_info to ouput_dirs
            with open(seg_info_output_path, "w", encoding="utf-8") as jsonData:
                json.dump(incoming_seg_info, jsonData, indent=4, sort_keys=True)
            # copy incoming_seg_info also to operator_in_dir bc subsequential nrrd2dcmseg operator needs seg_info.json there
            second_json_output_path = os.path.join(
                run_dir,
                self.batch_name,
                batch_element_dir,
                self.operator_in_dir,
                "seg_info.json",
            )
            shutil.copyfile(seg_info_output_path, second_json_output_path)

            # save incoming_metainfo to ouput_dirs
            with open(metainfo_output_path, "w", encoding="utf-8") as jsonData:
                json.dump(incoming_metainfo, jsonData, indent=4, sort_keys=True)
            # copy incoming_metainfo also to operator_in_dir bc subsequential nrrd2dcmseg operator needs seg_info.json there
            second_json_output_path = os.path.join(
                run_dir,
                self.batch_name,
                batch_element_dir,
                self.operator_in_dir,
                f"{self.name}.json",
            )
            shutil.copyfile(metainfo_output_path, second_json_output_path)

    def __init__(
        self,
        dag,
        name="rename-seg-label-names",
        metainfo_input_operator="",
        **kwargs,
    ):
        """ """
        self.metainfo_input_operator = metainfo_input_operator

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
