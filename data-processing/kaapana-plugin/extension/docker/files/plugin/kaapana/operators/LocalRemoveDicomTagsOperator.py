import datetime
from pathlib import Path
from subprocess import PIPE, run
from typing import List

import pydicom
import pytz
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings

logger = get_logger(__name__)
TIMEZONE = KaapanaSettings().timezone


class LocalRemoveDicomTagsOperator(KaapanaPythonBaseOperator):
    """
    Remove the dicom tags used to derive project and dataset name of incoming dicom data.
    """

    def __init__(
        self,
        dag,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name="remove-project-and-dataset-tag",
            python_callable=self.start,
            ram_mem_mb=10,
            **kwargs,
        )

    @cache_operator_output
    def start(self, **kwargs):
        run_dir: Path = Path(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folders: List[Path] = list((run_dir / self.batch_name).glob("*"))
        logger.info(f"Number of series: {len(batch_folders)}")
        for batch_element_dir in batch_folders:
            files: List[Path] = sorted(
                list((batch_element_dir / self.operator_in_dir).rglob(f"*.dcm"))
            )
            if len(files) == 0:
                raise FileNotFoundError(
                    f"No dicom file found in {batch_element_dir / self.operator_in_dir}"
                )
            logger.info(f"length {len(files)}")
            for dcm_file_path in files:
                logger.info(f"Remove tags for dicom file at {dcm_file_path}")
                remove_tags(dicom_path=dcm_file_path)


def remove_tags(
    dicom_path: str,
):
    """
    Process a DICOM file to check and modify ClinicalTrialProtocolID and ClinicalTrialSponsorName tags.

    Args:
        dicom_path (str): Path to the input DICOM file.
        default_project (str): Default value for ClinicalTrialProtocolID if the original value does not start with "kp-".
        default_dataset (str): Default value for ClinicalTrialSponsorName if the original value does not start with "kp-".

    Raises:
        InvalidDicomError: If the input file is not a valid DICOM file.
    """
    protocol_id_tag = (0x0012, 0x0020)
    sponsor_name_tag = (0x0012, 0x0010)
    cli_sponsor_name_tag = "0012,0010"
    cli_protocol_id_tag = "0012,0020"

    command = [
        "/usr/bin/dcmodify",
        "-e",
        f"{cli_sponsor_name_tag}",
        "-e",
        f"{cli_protocol_id_tag}",
        str(dicom_path),
    ]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    output.check_returncode()
