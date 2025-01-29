import os
from glob import glob
from subprocess import PIPE, run

from kaapanapy.helper import load_workflow_config
from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings, OperatorSettings

logger = get_logger(__name__, level="INFO")
from os.path import join

DEFAULT_PACS_HOST = f"ctp-dicom-service.{KaapanaSettings().services_namespace}.svc"
DEFAULT_PACS_PORT = 11112


class DcmSendOperator:

    def __init__(
        self,
        pacs_host: str,
        pacs_port: int,
        calling_ae_title_scu: str,
        called_ae_title_scp: str,
    ):
        # Load the workflow configuration
        self.conf = load_workflow_config()

        logger.info(self.conf)

        # Project information
        self.project = self.conf.get("project_form")
        self.project_name = self.project.get("name")

        # Airflow variables
        operator_settings = OperatorSettings()

        self.operator_in_dir = operator_settings.operator_in_dir
        self.workflow_dir = operator_settings.workflow_dir
        self.batch_name = operator_settings.batch_name
        self.run_id = operator_settings.run_id

        # PACS information
        self.pacs_host = pacs_host
        self.pacs_port = pacs_port

        # AE Titles
        # aet -> Dataset -> 0012,0010
        if calling_ae_title_scu:
            self.calling_ae_title_scu = calling_ae_title_scu
        else:
            logger.info("No calling AE title (SCU) set.")
            calling_ae_title_scu = self.conf.get("form_data").get("workflow_id")

            if not calling_ae_title_scu.startswith("kp-"):
                self.calling_ae_title_scu = f"kp-{calling_ae_title_scu}"

        # aec -> Project -> 0012,0020
        if called_ae_title_scp:
            self.called_ae_title_scp = called_ae_title_scp
        else:
            logger.info("No called AE title (SCP) set!")
            called_ae_title_scp = self.project_name
            if not called_ae_title_scp.startswith("kp-"):
                self.called_ae_title_scp = f"kp-{called_ae_title_scp}"

        logger.info(f"Calling AE Title (SCU): {self.calling_ae_title_scu}")
        logger.info(f"Called AE Title (SCP): {self.called_ae_title_scp}")
        logger.info(f"PACS Host: {self.pacs_host}")
        logger.info(f"PACS Port: {self.pacs_port}")

    def start(self):
        batch_folders = glob(join("/", self.workflow_dir, self.batch_name, "*"))

        for batch_element_dir in batch_folders:
            seg_element_input_dir = join(batch_element_dir, self.operator_in_dir)
            # Send data using pynetdicom
            logger.info(
                f"Sending data from {seg_element_input_dir} from project {self.project_name}"
            )

            env = dict(os.environ)
            command = [
                "dcmsend",
                "-v",
                f"{self.pacs_host}",
                f"{self.pacs_port}",
                "-aet",
                self.calling_ae_title_scu,
                "-aec",
                self.called_ae_title_scp,
                "--scan-directories",
                "--no-halt",
                f"{seg_element_input_dir}",
            ]

            max_retries = 5
            try_count = 0
            while try_count < max_retries:
                try:

                    output = run(
                        command,
                        stdout=PIPE,
                        stderr=PIPE,
                        universal_newlines=True,
                        env=env,
                        timeout=3600,
                    )

                    if output.returncode != 0 or "with status SUCCESS" not in str(
                        output
                    ):
                        logger.error(f"Error sending data: {output.stderr}")
                        logger.info(f"Retry {try_count + 1}/{max_retries}")
                        try_count += 1
                except Exception as e:
                    logger.error(f"Error sending data: {e}")
                    logger.info(f"Retry {try_count + 1}/{max_retries}")
                    try_count += 1

            if try_count >= max_retries:
                raise ValueError(
                    f"Error sending data: {output.stderr} after {max_retries} retries"
                )


if __name__ == "__main__":

    pacs_host = (
        os.getenv("PACS_HOST")
        if os.getenv("PACS_HOST", "") != ""
        else DEFAULT_PACS_HOST
    )

    pacs_port = (
        int(os.getenv("PACS_PORT"))
        if os.getenv("PACS_PORT", "") != ""
        else DEFAULT_PACS_PORT
    )

    # aet -> Dataset -> 0012,0010
    calling_ae_title_scu = (
        os.getenv("CALLING_AE_TITLE_SCU")
        if os.getenv("CALLING_AE_TITLE_SCU", "") != ""
        else None
    )

    # aec -> Project -> 0012,0020
    called_ae_title_scp = (
        os.getenv("OP_CALLED_AE_TITLE_SCP")
        if os.getenv("OP_CALLED_AE_TITLE_SCP", "") != ""
        else None
    )

    operator = DcmSendOperator(
        pacs_host=pacs_host,
        pacs_port=pacs_port,
        calling_ae_title_scu=calling_ae_title_scu,
        called_ae_title_scp=called_ae_title_scp,
    )
    operator.start()
