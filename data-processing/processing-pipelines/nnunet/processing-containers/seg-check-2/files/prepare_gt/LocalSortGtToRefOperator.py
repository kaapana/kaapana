import glob
import os
import shutil
from datetime import timedelta
from os.path import join,exists,basename 
import logging
from logger_helper import get_logger
from pathlib import Path

from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

class LocalSortGtToRefOperator(KaapanaPythonBaseOperator):
    """
    Operator sorts multiple segmentations to its base images.

    """
    def start(self, **kwargs):
        input_file_extension = "*.nii.gz"
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dir = join(run_dir, self.batch_name)
        batch_output_dir = join(batch_dir,self.operator_out_dir)
        batch_folders = [
            f for f in glob.glob(os.path.join(batch_dir, "*"))
        ]
        for batch_element_dir in batch_folders:
            self.logger.info("input operator ", self.operator_in_dir)
            element_input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
            
            gt_mask_niftis = glob(join(element_input_dir, input_file_extension), recursive=False)
            base_ref_niftis = glob(join(element_input_dir, input_file_extension), recursive=False)
            self.logger.info(f"# Found {len(base_ref_niftis)} input-files!")
            assert len(base_ref_niftis) == 1
            base_ref_image_uid = basename(base_ref_niftis[0]).replace("nii.gz","")
            gt_target_dir = join(batch_output_dir,base_ref_image_uid)
            Path(gt_target_dir).mkdir(parents=True, exist_ok=True)

            for gt_mask_nifti in gt_mask_niftis:
                target_move_path= join(gt_target_dir,basename(gt_mask_nifti))
                if exists(target_move_path):
                    self.logger.warning(f"Mask {basename(gt_mask_nifti)} already exists in target dir! -> skipping")
                    continue

                if self.move_files:
                    self.logger.info(f"Moving {gt_mask_nifti.replace(batch_dir,'')} -> {target_move_path.replace(batch_dir,'')} ...")
                    shutil.move(gt_mask_nifti,target_move_path)
                else:
                    self.logger.info(f"Copy {gt_mask_nifti.replace(batch_dir,'')} -> {target_move_path.replace(batch_dir,'')} ...")
                    shutil.copy2(gt_mask_nifti,target_move_path)

    def __init__(
        self,
        dag,
        move_files: bool = False,
        log_level: str = "info",
        **kwargs,
    ):
        """
        :param operator_in_dir: Referenced base image NIFTI folder
        :param move_files: Select if files should be move (True) or copied (False)
        :param log_level:  Select one of the log-levels (debug,info,warning,critical,error)
        """

        self.move_files = move_files
        self.name = "sort-gt-to-ref"
        self.task_id = self.name

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
            dag=dag,
            task_id=self.task_id,
            name=self.name,
            python_callable=self.start,
            execution_timeout=timedelta(minutes=10),
            **kwargs,
        )
