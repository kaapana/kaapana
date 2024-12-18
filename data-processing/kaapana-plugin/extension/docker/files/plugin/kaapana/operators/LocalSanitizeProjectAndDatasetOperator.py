from pathlib import Path
from typing import List
from subprocess import PIPE, run
import datetime
import pydicom
import pytz
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings

logger = get_logger(__name__)
TIMEZONE = KaapanaSettings().timezone


class LocalSanitizeProjectAndDatasetOperator(KaapanaPythonBaseOperator):
    """
    Sanitizes the dicom tags used to derive project and dataset name of incoming dicom data.

    Check, that the the value of 00120020 ClinicalTrialProtocolID_keyword complies with the format kp-<project name>
        If the tag complies: Remove the prefix kp- and update the tag in the dicom meta header
        If the tag does not comply: Overwrite 00120020 ClinicalTrialProtocolID_keyword with the default project "admin"

    Check, that the the value of 00120010 ClinicalTrialSponsorName_keyword complies with the format kp-<dataset name>
        If the tag complies: Remove the prefix kp- and update the tag in the dicom meta header
        If the tag does not comply: Overwrite 00120010 ClinicalTrialSponsorName_keyword with a timestamp, when this operator starts.
    """

    def __init__(
        self,
        dag,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            name="sanitize-dicom-project-and-dataset",
            python_callable=self.start,
            ram_mem_mb=10,
            **kwargs,
        )

    @cache_operator_output
    def start(self, **kwargs):
        timestamp = datetime.datetime.now(pytz.timezone(TIMEZONE)).strftime(
            "%y-%m-%d-%H:%M:%S%f"
        )
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
                logger.info(f"Override metadata: {dcm_file_path}")
                sanitize_project_and_dataset_tag(
                    dicom_path=dcm_file_path, default_dataset=timestamp
                )


def sanitize_project_and_dataset_tag(
    dicom_path: str,
    default_project: str = "admin",
    default_dataset: str = "default-dataset",
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

    sanitized_protocol_id_value = default_project
    sanitized_sponsor_name_value = default_dataset

    # Read the DICOM file
    with pydicom.dcmread(
        dicom_path,
        stop_before_pixels=False,
        specific_tags=[protocol_id_tag, sponsor_name_tag],
    ) as ds:
        # Process ClinicalTrialProtocolID (0012,0020)
        if protocol_id_tag in ds:
            protocol_id = ds.get(protocol_id_tag, "")
            if protocol_id.value.startswith("kp-"):
                sanitized_protocol_id_value = protocol_id[3:]  # Remove "kp-" prefix

        # Process ClinicalTrialSponsorName (0012,0010)
        if sponsor_name_tag in ds:
            sponsor_name = ds.get(sponsor_name_tag, "")
            if sponsor_name.value.startswith("kp-"):
                sanitized_sponsor_name_value = sponsor_name[3:]  # Remove "kp-" prefix

    command = [
        "/usr/bin/dcmodify",
        "-i",
        f"{cli_sponsor_name_tag}={sanitized_sponsor_name_value}",
        "-i",
        f"{cli_protocol_id_tag}={sanitized_protocol_id_value}",
        str(dicom_path),
    ]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    output.check_returncode()
