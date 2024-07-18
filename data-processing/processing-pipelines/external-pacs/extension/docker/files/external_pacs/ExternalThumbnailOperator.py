import json
import logging
from pathlib import Path
from typing import List

from kaapana.kubetools.secret import get_k8s_secret, hash_secret_name
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperDcmWebGcloud import DcmWebGcloudHelper
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__file__)


class ExternalThumbnailOperator(KaapanaPythonBaseOperator):
    def __init__(
        self,
        dag,
        name: str = "external_thumbnail_operator",
        **kwargs,
    ):
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)

    @cache_operator_output
    def start(self, ds, **kwargs):
        workflow_form = kwargs["dag_run"].conf["workflow_form"]
        dcmweb_endpoint = workflow_form["dcmweb_endpoint"]
        secret_name = hash_secret_name(dcmweb_endpoint=dcmweb_endpoint)
        secret = get_k8s_secret(secret_name=secret_name)

        if not secret:
            logger.error("Invalid credentials/secret")
            exit(1)

        helper = DcmWebGcloudHelper(
            dcmweb_endpoint=dcmweb_endpoint,
            service_account_info=secret,
        )

        if not helper.check_reachability():
            logger.error(f"Cannot reach {dcmweb_endpoint} with provided credentials.")
            logger.error("Not saving credentials and exiting!")
            exit(1)

        run_dir: Path = Path(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folders: List[Path] = list((run_dir / self.batch_name).glob("*"))
        logger.info(f"Number of series: {len(batch_folders)}")

        for batch_element_dir in batch_folders:
            files: List[Path] = sorted(
                list((batch_element_dir / self.operator_in_dir).rglob("*.json"))
            )

            if len(files) == 0:
                raise FileNotFoundError(
                    f"No json file found in {batch_element_dir / self.operator_in_dir}"
                )

            file_path = files[0]

            target_dir: Path = batch_element_dir / self.operator_out_dir
            target_dir.mkdir(exist_ok=True)

            with open(file_path, "r") as f:
                metadata = json.load(f)

            study_uid = metadata["0020000D StudyInstanceUID_keyword"]
            series_uid = metadata["0020000E SeriesInstanceUID_keyword"]

            helper.thumbnail(
                study_uid=study_uid,
                series_uid=series_uid,
                target_dir=target_dir,
            )
            logger.info("Thumbnail saved successfully")
