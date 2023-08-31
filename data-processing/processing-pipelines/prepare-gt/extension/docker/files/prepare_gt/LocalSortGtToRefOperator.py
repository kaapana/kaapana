import os
import shutil
from datetime import timedelta
from os.path import join, exists, basename, dirname
import logging
from logger_helper import get_logger
from glob import glob
from pathlib import Path
import pydicom
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalSortGtToRefOperator(KaapanaPythonBaseOperator):
    """
    Operator sorts multiple segmentations to its base images.

    """

    def start(self, **kwargs):
        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_dir = join(run_dir, self.batch_name)
        new_batch_output_dir = join(run_dir, self.new_batch_name)
        batch_folders = [f for f in glob(os.path.join(batch_dir, "*"))]
        for batch_element_dir in batch_folders:
            element_base_input_dir = join(batch_element_dir, self.base_dcm_folder)
            element_gt_input_dir = join(batch_element_dir, self.gt_dcm_folder)

            if (
                not exists(element_base_input_dir)
                and not exists(element_gt_input_dir)
                and self.move_files
            ):
                self.logger.info(
                    f"Batch element {basename(batch_element_dir)} already moved -> continue"
                )
                continue

            base_dcms = glob(join(element_base_input_dir, "*"), recursive=False)
            self.logger.info(f"{element_base_input_dir=}")

            if not len(base_dcms) > 1:
                self.logger.warning(
                    f"Batch element {basename(batch_element_dir)} no base-image found -> continue"
                )
                continue

            base_series_uid = str(pydicom.dcmread(base_dcms[0])[0x0020, 0x000E].value)
            target_dir = join(new_batch_output_dir, base_series_uid)
            Path(dirname(target_dir)).mkdir(parents=True, exist_ok=True)

            base_dcm_target_dir = join(target_dir, basename(element_base_input_dir))
            gt_dcm_target_dir = join(target_dir, basename(element_gt_input_dir))

            self.logger.info(
                f"COPY {element_base_input_dir.replace(batch_dir,'')} -> {base_dcm_target_dir.replace(batch_dir,'')} ..."
            )
            shutil.copytree(
                element_base_input_dir, base_dcm_target_dir, dirs_exist_ok=True
            )
            self.logger.info(
                f"COPY   {element_gt_input_dir.replace(batch_dir,'')} -> {gt_dcm_target_dir.replace(batch_dir,'')} ..."
            )
            shutil.copytree(element_gt_input_dir, gt_dcm_target_dir, dirs_exist_ok=True)
            if self.move_files:
                self.logger.info(
                    f"Removing {element_base_input_dir.replace(batch_dir,'')} ..."
                )
                shutil.rmtree(element_base_input_dir)
                self.logger.info(
                    f"Removing {element_gt_input_dir.replace(batch_dir,'')} ..."
                )
                shutil.rmtree(element_gt_input_dir)

    def __init__(
        self,
        dag,
        base_dcm_operator,
        gt_dcm_operator,
        move_files: bool = False,
        new_batch_name: str = "sorted",
        log_level: str = "info",
        **kwargs,
    ):
        """
        :param base_nifti_operator: Referenced base image NIFTI operator (usually LocalGetRefSeriesOperator)
        :param gt_nifti_operator: Converted segmentation NIFTIs operator (usally Mask2nifitiOperator)
        :param move_files: Select if files should be move (True) or copied (False)
        :param log_level:  Select one of the log-levels (debug,info,warning,critical,error)
        """

        self.base_dcm_folder = base_dcm_operator.operator_out_dir
        self.gt_dcm_folder = gt_dcm_operator.operator_out_dir
        self.move_files = move_files
        self.new_batch_name = new_batch_name
        self.name = "reorder-ref2gt"
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
