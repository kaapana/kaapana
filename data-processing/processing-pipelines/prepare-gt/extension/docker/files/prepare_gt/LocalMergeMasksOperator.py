from glob import glob
from pathlib import Path
import logging
import json
from os.path import join, exists, basename, dirname
from logger_helper import get_logger
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
import nibabel as nib
import numpy as np


class LocalMergeMasksOperator(KaapanaPythonBaseOperator):
    """
    Operator to remove series from PACS system.

    **Inputs:**

    * Input data which should be removed given by input parameter: input_operator.
    """

    def start(self, ds, **kwargs):
        master_label_dict = {}
        input_file_extension = "*.nii.gz"

        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [f for f in glob(join(run_dir, self.batch_name, "*"))]

        master_label_dict_path = join(
            run_dir, "get-master-label-list", "master_label_list.json"
        )
        self.logger.info(f"{self.batch_name=}")
        self.logger.info(f"{self.operator_in_dir=}")
        self.logger.info(f"{self.operator_out_dir=}")
        self.logger.info(f"{master_label_dict_path=}")

        assert exists(master_label_dict_path)
        with open(master_label_dict_path) as f:
            master_label_dict = json.load(f)

        for batch_element_dir in batch_folder:
            local_seg_dict = {}
            element_input_dir = join(batch_element_dir, self.operator_in_dir)
            element_output_dir = join(batch_element_dir, self.operator_out_dir)
            Path(element_output_dir).mkdir(parents=True, exist_ok=True)

            gt_mask_niftis = glob(
                join(element_input_dir, input_file_extension), recursive=False
            )

            merged_mask = None
            for gt_mask_nifti in gt_mask_niftis:
                base_id = basename(gt_mask_nifti).replace(".nii.gz", "")
                assert len(base_id.split("--")) == 3
                integer_encoding = base_id.split("--")[1]
                label_name = base_id.split("--")[2]
                self.logger.info(f"{integer_encoding=}")
                self.logger.info(f"{label_name=}")

                assert label_name in master_label_dict

                if isinstance(master_label_dict[label_name], str):
                    target_encoding = master_label_dict[master_label_dict[label_name]]
                    new_label_name = master_label_dict[label_name]
                elif isinstance(master_label_dict[label_name], int):
                    target_encoding = master_label_dict[label_name]
                    new_label_name = label_name
                else:
                    self.logger.error("Something went wrong.")
                    exit(1)

                if new_label_name not in local_seg_dict:
                    local_seg_dict[new_label_name] = target_encoding

                self.logger.info(f"Loading mask {basename(gt_mask_nifti)}")
                mask_loaded = nib.load(gt_mask_nifti)
                self.logger.info(f"Loading Nifti ... ")
                mask_numpy = mask_loaded.get_fdata().astype(np.uint8)

                if np.max(mask_numpy) > int(integer_encoding):
                    self.logger.error(f"{np.max(mask_numpy)}")
                    exit(1)

                if merged_mask is None:
                    self.logger.info(f"Creating empty merge-mask ...")
                    merged_mask = np.empty_like(mask_numpy, dtype=np.uint8)
                    affine = mask_loaded.affine
                    header = mask_loaded.header
                elif mask_numpy.shape != merged_mask.shape:
                    self.logger.error(
                        f"Shape missmatch: {mask_numpy.shape=} vs {merged_mask.shape=}"
                    )
                    exit(1)

                self.logger.info(
                    f"Setting target encoding: {integer_encoding} -> {target_encoding}"
                )
                mask_numpy[mask_numpy == integer_encoding] = target_encoding

                self.logger.info(f"Merging masks ... ")
                merged_mask = np.where(merged_mask == 0, merged_mask, mask_numpy)

                self.logger.info(f"Mask {label_name} done ")

            seg_info = {
                "algorithm": "Mask-Merger",
                "seg_info": [],
            }
            seg_info_path = join(element_output_dir, "seg_info.json")

            self.logger.info(f"Generating {seg_info_path} ...")
            for key, value in local_seg_dict.items():
                seg_info["seg_info"].append(
                    {
                        "label_name": key,
                        "label_int": str(value),
                    }
                )
            with open(seg_info_path, "w") as f:
                json.dump(seg_info, indent=4, fp=f)

            merged_nifti_path = join(element_output_dir, "merged.nii.gz")
            self.logger.info(f"Saving merged nifti @ {merged_nifti_path} ...")
            merged_mask_nii = nib.Nifti1Image(merged_mask, affine, header)
            nib.save(merged_mask_nii, merged_nifti_path)
            self.logger.info(f"Finished")

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
            dag=dag, name="merge-masks", python_callable=self.start, **kwargs
        )


if __name__ == "__main__":
    test = LocalMergeMasksOperator()
    print()
