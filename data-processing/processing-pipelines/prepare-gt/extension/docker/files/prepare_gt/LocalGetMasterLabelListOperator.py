from glob import glob
from pathlib import Path
import logging
import json
from os.path import join, exists, basename, dirname
from logger_helper import get_logger
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class LocalGetMasterLabelListOperator(KaapanaPythonBaseOperator):
    """
    Operator to remove series from PACS system.

    This operator removes either selected series or whole studies from Kaapana's integrated research PACS system by DCM4Chee.
    The operaator relies on "delete_study" function of Kaapana's "HelperDcmWeb" operator.

    **Inputs:**

    * Input data which should be removed given by input parameter: input_operator.
    """

    def start(self, ds, **kwargs):
        master_label_dict = {}
        input_file_extension = "*.nii.gz"

        conf = kwargs["dag_run"].conf
        print("conf", conf)
        self.merge_segs_config = None
        if (
            "form_data" in conf
            and conf["form_data"] is not None
            and "merge_segs_config" in conf["form_data"]
        ):
            conf_value = conf["form_data"]["merge_segs_config"]
            self.logger.info(f"{conf_value=}")
            self.merge_segs_config = (
                None
                if conf_value is None
                or conf_value == ""
                or conf_value.lower() == "none"
                else conf_value
            )
            self.logger.info(f"{self.merge_segs_config=}")

        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [f for f in glob(join(run_dir, self.batch_name, "*"))]

        batch_output_dir = join(run_dir, self.operator_out_dir)
        self.logger.info(f"{batch_output_dir=}")
        self.logger.info(f"{self.batch_name=}")
        self.logger.info(f"{self.operator_in_dir=}")
        self.logger.info(f"{self.operator_out_dir=}")
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        for batch_element_dir in batch_folder:
            element_input_dir = join(batch_element_dir, self.operator_in_dir)
            gt_mask_niftis = glob(
                join(element_input_dir, input_file_extension), recursive=False
            )

            for gt_mask_nifti in gt_mask_niftis:
                base_id = basename(gt_mask_nifti).replace(".nii.gz", "")
                assert len(base_id.split("--")) == 3
                integer_encoding = base_id.split("--")[1]
                label_name = base_id.split("--")[2]

                if label_name not in master_label_dict:
                    master_label_dict[label_name] = {
                        "count": 1,
                        "integer_encodings": {str(integer_encoding): 1},
                        "merge_label_to": None,
                    }
                else:
                    master_label_dict[label_name]["count"] += 1
                    if (
                        str(integer_encoding)
                        in master_label_dict[label_name]["integer_encodings"]
                    ):
                        master_label_dict[label_name]["integer_encodings"][
                            str(integer_encoding)
                        ] += 1
                    else:
                        master_label_dict[label_name]["integer_encodings"][
                            str(integer_encoding)
                        ] = 1

        master_label_dict = {
            k: v
            for k, v in sorted(
                master_label_dict.items(),
                key=lambda item: item[1]["count"],
                reverse=True,
            )
        }
        print("(master_label_dict:")
        print(json.dumps(master_label_dict, indent=4))

        if self.merge_segs_config is not None:
            for merge_config in self.merge_segs_config.split(";"):
                if not "->" in merge_config:
                    print(
                        f"Issues with merge config ({merge_config}) detected! -> it needs to follow the scheme label_to_merge1,label_to_merge2,...->label_to_be_merged_to"
                    )
                    print(
                        "eg: 'Lung-Right,Lung-Left->lung;Lung_R,Lung_L->lung;spinal cord,Spinal-Cord->spinal-cord'"
                    )
                    exit(1)

                merge_to_label = merge_config.split("->")[-1]
                for label_to_be_merged in merge_config.split("->")[0].split(","):
                    if label_to_be_merged in master_label_dict:
                        master_label_dict[label_to_be_merged][
                            "merge_label_to"
                        ] = merge_to_label

        output_dict = {}
        encoding_index = 1
        for label, label_values in master_label_dict.items():
            if label not in output_dict:
                if label_values["merge_label_to"] is not None:
                    if label_values["merge_label_to"] not in output_dict:
                        output_dict[label_values["merge_label_to"]] = encoding_index
                        encoding_index += 1
                    output_dict[label] = label_values["merge_label_to"]
                else:
                    output_dict[label] = encoding_index
                    encoding_index += 1

        with open(join(batch_output_dir, "master_label_list.json"), "w") as f:
            json.dump(output_dict, indent=4, fp=f)

    def __init__(
        self,
        dag,
        log_level: str = "info",
        **kwargs,
    ):
        """
        :param delete_complete_study: Specifies the amount of removed data to all series of a specified study.
        """
        log_level_int = None
        if log_level == "debug":
            log_level_int = logging.DEBUG
        elif log_level == "info":
            log_level_int = logging.INFO
        elif log_level == "warning":
            log_level_int = logging.WARNING
        elif log_level == "critical":
            log_level_int = logging.CRITICAL
        elif log_level == "error":
            log_level_int = logging.ERROR

        self.logger = get_logger(__name__, log_level_int)

        super().__init__(
            dag=dag, name="get-master-label-list", python_callable=self.start, **kwargs
        )
