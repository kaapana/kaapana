import os
import tempfile
import time
from glob import glob
from pathlib import Path
from typing import List, Optional

import pydicom
import requests
from dicomweb_client import DICOMwebClient
from kaapana.blueprints.kaapana_global_variables import (
    OIDC_CLIENT_SECRET,
    SERVICES_NAMESPACE,
    SYSTEM_USER_PASSWORD,
)
from kaapana.operators.DcmWeb import DcmWeb, DcmWebException
from kaapanapy.helper import get_project_user_access_token
from kaapanapy.logger import get_logger

logger = get_logger(__file__)


class DcmWebLocalHelper(DcmWeb):

    def __init__(self, application_entity: str):
        self.dcm4chee_endpoint = (
            f"http://dcm4chee-service.{SERVICES_NAMESPACE}.svc:8080/dcm4chee-arc/aets"
        )
        self.application_entity = application_entity
        dcmweb_endpoints = {
            "rs": f"{self.dcm4chee_endpoint}/{self.application_entity}/rs",
            "wado": f"{self.dcm4chee_endpoint}/{self.application_entity}/wado",
        }

        access_token = get_project_user_access_token()
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "x-forwarded-access-token": access_token,
        }

        self.aet_rejection_stage = "IOCM_QUALITY"
        session = requests.Session()
        session.headers.update(auth_headers)

        client = DICOMwebClient(
            url=dcmweb_endpoints["rs"],
            headers=auth_headers,
        )
        super().__init__(dcmweb_endpoints, session, client)

    def search_instances_of_study(
        self, study_uid: str, application_entity: Optional[str] = None
    ) -> requests.Response:
        if application_entity:
            url = f"{self.dcm4chee_endpoint}/{application_entity}/rs/studies/{study_uid}/instances"
        else:
            url = f"{self.dcmweb_endpoints['rs']}/studies/{study_uid}/instances"
        response = self.session.get(url)
        return response

    def reject_study(self, study_uid: str):
        logger.info(f"Rejecting study {study_uid}")
        url = f"{self.dcmweb_endpoints['rs']}/studies/{study_uid}/reject/113001%5EDCM"
        response = self.session.post(url)
        response.raise_for_status()
        return response

    def delete_study(self, study_uid: str):
        logger.info(f"Deleting study {study_uid}")
        response = self.search_instances_of_study(study_uid=study_uid)
        if response.status_code != 200:
            logger.warning(f"Study {study_uid} does not exist in PACS")
            return

        logger.info("1/2: rejecting study")
        response = self.reject_study(study_uid=study_uid)

        logger.info("Awaiting rejection to complete")
        time.sleep(5)
        logger.info("Rejection complete")
        # After the rejection there can be Key Object Selection Document Storage left on the pacs,
        # these will disapear when the study is finaly deleted, so a check
        # may still return results in this spot

        logger.info("2/2: deleting study")

        response = self.search_instances_of_study(
            study_uid=study_uid, application_entity=self.aet_rejection_stage
        )
        if response.status_code != 200:
            raise DcmWebException(
                f"Could not find study {study_uid} in aet {self.aet_rejection_stage}"
            )
        logger.info(f"Found study {study_uid} in aet {self.aet_rejection_stage}")

        url = f"{self.dcm4chee_endpoint}/{self.aet_rejection_stage}/rs/studies/{study_uid}"
        logger.info(f"Sending delete request {url}")
        response = self.session.delete(url)
        if not response.ok and response.status_code != 204:
            raise DcmWebException(
                f"Error deleting study from {self.aet_rejection_stage} errorcode: {response.status_code} content {response.content}"
            )

        logger.info("Request Successful, awaiting deletion to complete")
        time.sleep(5)
        for ae in [self.aet_rejection_stage, self.application_entity]:
            logger.info(f"Check if study is removed from {ae}")
            if self.search_instances_of_study(study_uid, ae):
                raise DcmWebException(f"Deletion of study {study_uid} failed")

        logger.info(f"Deletion of {study_uid} complete")

    def delete_series(self, study_uid: str, series_uids: List[str]):
        logger.info(f"Deleting series {series_uids} in study {study_uid}")
        response = self.search_series_of_study(study_uid)
        if response.status_code != 200:
            logger.warning(f"Could find any series of a study {study_uid} to delete")
            return

        series_uids_keep = [s["0020000E"]["Value"][0] for s in response.json()]

        logger.warning(f"{series_uids_keep=}")
        logger.warning(f"{series_uids=}")

        for series_uid in series_uids:
            if series_uid not in series_uids_keep:
                logger.warn(
                    f"Series {series_uid} does not exist for study {study_uid} on PACS",
                )
                continue
            series_uids_keep.remove(series_uid)

        with tempfile.TemporaryDirectory() as tmp_dir:
            logger.info(f"1/4 Start Downloading all series to keep to {tmp_dir}")
            for keep_series_uid in series_uids_keep:
                logger.info(f"Downloading Series {keep_series_uid} to {tmp_dir}")
                if not self.retrieve_series(
                    series_uid=keep_series_uid,
                    target_dir=Path(tmp_dir),
                    include_series_dir=True,
                ):
                    raise DcmWebException(f"Could not download {keep_series_uid}")
                logger.info("Done")
            logger.info(f"Downloaded all series to keep to {tmp_dir}")

            logger.info(f"2/4 Delete complete study from pacs {tmp_dir}")
            self.delete_study(study_uid)
            logger.info("Study deleted")

            logger.info("3/4 Upload series to keep again to PACS")
            for upload_series_uid in series_uids_keep:
                logger.info(f"Upload series {upload_series_uid}")
                self.upload_dcm_files(Path(tmp_dir) / upload_series_uid)

            logger.info("4/4 Delete temp files")
            # deletion of tmp_files should happen automatically if scope of tmp_dir is left

        if self.search_instances_of_series(study_uid, series_uid):
            raise DcmWebException(f"Series {series_uid} still exists after deletion")
        logger.info(f"Series {series_uid} sucessfully deleted")

    def upload_dcm_files(self, path: Path):
        files = glob(os.path.join(path, "*.dcm"))
        total_files = len(files)
        uploaded_fiels = 0

        for file in files:
            uploaded_fiels += 1
            logger.info("Uploading %d / %d:  %s", uploaded_fiels, total_files, file)
            dataset = pydicom.dcmread(file)
            self.client.store_instances(datasets=[dataset])
