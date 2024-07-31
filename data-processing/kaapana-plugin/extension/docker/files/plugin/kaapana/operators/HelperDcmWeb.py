import json
import os
import tempfile
import time
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Optional

import pydicom
import requests
from dicomweb_client import DICOMwebClient
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapanapy.helper import get_project_user_access_token
from kaapanapy.logger import get_logger

logger = get_logger(__file__)


def get_dcmweb_helper(
    dcmweb_endpoint: str,
    application_entity: str = "KAAPANA",
    service_account_info: Dict[str, str] | None = None,
):
    if not dcmweb_endpoint:
        from kaapana.operators.HelperDcmWeb import DcmWebLocalHelper

        return DcmWebLocalHelper(application_entity=application_entity)

    if "google" in dcmweb_endpoint and service_account_info:
        from kaapana.operators.HelperDcmWebGcloud import DcmWebGcloudHelper

        return DcmWebGcloudHelper(
            dcmweb_endpoint=dcmweb_endpoint,
            service_account_info=service_account_info,
        )
    else:
        from kaapana.operators.HelperDcmWeb import DcmWebLocalHelper

        logger.error(f"Unknown dcmweb_endpoint: {dcmweb_endpoint}")
        logger.error("Defaulting to the local dcm4chee")
        return DcmWebLocalHelper(application_entity=application_entity)


class DcmWebLocalHelper:
    REJECTION_APPLICATION_ENTITY = "IOCM_QUALITY"
    DCMWEB_ENDPOINT = (
        f"http://dcm4chee-service.{SERVICES_NAMESPACE}.svc:8080/dcm4chee-arc/aets"
    )

    def __init__(self, application_entity: str):
        self.rs_endpoint = f"{self.DCMWEB_ENDPOINT}/{application_entity}/rs/"
        self.rejection_endpoint = f"{self.DCMWEB_ENDPOINT}/{DcmWebLocalHelper.REJECTION_APPLICATION_ENTITY}/rs/"
        self.wado_endpoint = f"{self.DCMWEB_ENDPOINT}/{application_entity}/wado/"
        self.application_entity = application_entity
        access_token = get_project_user_access_token()
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "x-forwarded-access-token": access_token,
        }

        self.session = requests.Session()
        self.session.headers.update(auth_headers)
        self.client = DICOMwebClient(
            url=self.rs_endpoint,
            headers=auth_headers,
        )

    def __str__(self):
        return self.rs_endpoint

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        data: Any = None,
    ) -> Optional[Dict | List[Dict]]:
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except requests.HTTPError as e:
            logger.error(
                f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            )
        except requests.RequestException as e:
            logger.error(f"Request error occurred: {e}")
        except ValueError as e:
            logger.error(f"JSON decoding failed: {e}")
        return None

    def check_reachability(self) -> bool:
        for i in range(10):
            try:
                if self.search_for_series() is not None:
                    return True
            except Exception as e:
                logger.error(f"Connecting to PACS failed: {e}. Retry {i}")
                time.sleep(1)

        logger.error(
            f"Dcmweb endpoint: {self.rs_endpoint} is not available or wrong credentials."
        )
        return False

    def check_if_series_in(self, series_uid: str) -> bool:
        for attempt in range(1, 31):
            series = self.search_for_series({"SeriesInstanceUID": series_uid})
            if series is not None:
                return True
            logger.error(
                f"Attempt {attempt}/30: Error checking for series {series_uid} in PACS."
            )
            time.sleep(2)

        logger.error(f"Series {series_uid} not found in PACS after 30 attempts.")
        return False

    def retrieve_series(
        self,
        series_uid: str,
        target_dir: Path,
        include_series_dir: Optional[bool] = False,
    ) -> bool:
        instances = self.search_for_instances({"SeriesInstanceUID": series_uid})
        if instances is None:
            logger.error(f"Failed to request series UID: {series_uid}")
            return False

        object_uids = [
            (
                obj["0020000D"]["Value"][0],  # StudyInstanceUID
                obj["00080018"]["Value"][0],  # SOPInstanceUID
            )
            for obj in instances
        ]

        if include_series_dir:
            target_dir /= series_uid
        target_dir.mkdir(parents=True, exist_ok=True)

        for study_uid, object_uid in object_uids:
            if not self.retrieve_object(
                study_uid=study_uid,
                series_uid=series_uid,
                object_uid=object_uid,
                target_dir=target_dir,
            ):
                return False

        return True

    def reject_study(self, study_uid: str) -> bool:
        logger.info(f"Rejecting study {study_uid}")
        url = f"{self.rs_endpoint}/studies/{study_uid}/reject/113001%5EDCM"
        response = self._make_request(url, method="POST")
        return response is not None

    def delete_study(self, study_uid: str) -> None:
        logger.info(f"Deleting study {study_uid}")
        instances = self.search_instances_of_study(study_uid)
        if instances is None:
            logger.warning(f"Study {study_uid} does not exist in PACS")
            return

        logger.info("1/2: rejecting study")
        if not self.reject_study(study_uid):
            logger.error(f"Failed to reject study {study_uid}")
            return

        logger.info("Awaiting rejection to complete")
        time.sleep(5)
        logger.info("Rejection complete")

        logger.info("2/2: deleting study")
        url = f"{self.rs_endpoint}/studies/{study_uid}"
        response = self._make_request(url, method="DELETE")
        if response is not None:
            raise Exception(f"Error deleting study {study_uid}: {response}")

        logger.info("Request Successful, awaiting deletion to complete")
        time.sleep(5)

    def delete_series(self, study_uid: str, series_uids: List[str]) -> None:
        logger.info(f"Deleting series {series_uids} in study {study_uid}")
        try:
            series = self.search_series_of_study(study_uid)
        except json.decoder.JSONDecodeError:
            logger.warning(f"Could not find any series of study {study_uid} to delete")
            return

        series_uids_keep = [s["0020000E"]["Value"][0] for s in series]

        for series_uid in series_uids:
            if series_uid not in series_uids_keep:
                logger.warning(
                    f"Series {series_uid} does not exist for study {study_uid} on PACS"
                )
                continue
            series_uids_keep.remove(series_uid)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            logger.info(f"1/4 Start Downloading all series to keep to {tmp_dir}")
            for keep_series_uid in series_uids_keep:
                logger.info(f"Downloading Series {keep_series_uid} to {tmp_dir}")
                if not self.retrieve_series(
                    keep_series_uid, tmp_dir_path, include_series_dir=True
                ):
                    raise Exception(f"Could not download {keep_series_uid}")
                logger.info("Done")

            logger.info(f"Downloaded all series to keep to {tmp_dir}")

            logger.info("2/4 Delete complete study from PACS")
            self.delete_study(study_uid)
            logger.info("Study deleted")

            logger.info("3/4 Upload series to keep again to PACS")
            for upload_series_uid in series_uids_keep:
                logger.info(f"Upload series {upload_series_uid}")
                self.upload_dcm_files(tmp_dir_path / upload_series_uid)

            logger.info("4/4 Delete temp files")

        if self.search_instances_of_series(study_uid, series_uid):
            raise Exception(f"Series {series_uid} still exists after deletion")
        logger.info(f"Series {series_uid} successfully deleted")

    def upload_dcm_files(self, path: Path):
        files = glob(os.path.join(path, "*.dcm"))
        total_files = len(files)
        uploaded_fiels = 0

        for file in files:
            uploaded_fiels += 1
            logger.info("Uploading %d / %d:  %s", uploaded_fiels, total_files, file)
            dataset = pydicom.dcmread(file)
            self.client.store_instances(datasets=[dataset])

    def retrieve_object(
        self,
        study_uid: str,
        series_uid: str,
        object_uid: str,
        target_dir: Path,
    ):
        payload = {
            "requestType": "WADO",
            "studyUID": study_uid,
            "seriesUID": series_uid,
            "objectUID": object_uid,
            "contentType": "application/dicom",
        }
        logger.debug(payload)
        response = self.session.get(self.wado_endpoint, params=payload)

        if response.status_code != 200:
            logger.error("Download of object was not successful")
            logger.error(f"SeriesUID: {series_uid}")
            logger.error(f"StudyUID: {study_uid}")
            logger.error(f"objectUID: {object_uid}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(f"Response content: {response.content}")
            return False

        filename = object_uid + ".dcm"
        filepath = target_dir / filename
        with open(filepath, "wb") as f:
            f.write(response.content)

        return True

    def search_rejected_instances_of_study(self, study_uid: str) -> List[Dict]:
        url = f"{self.rejection_endpoint}/studies/{study_uid}/instances"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def search_instances_of_study(self, study_uid: str) -> List[Dict]:
        url = f"{self.rs_endpoint}/studies/{study_uid}/instances"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def search_instances_of_series(self, study_uid: str, series_uid: str) -> List[Dict]:
        url = f"{self.rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def search_series_of_study(self, study_uid: str) -> List[Dict]:
        url = f"{self.rs_endpoint}/studies/{study_uid}/series"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def search_for_series(self, search_filters: Dict = {}) -> List[Dict]:
        url = f"{self.rs_endpoint}/series"
        response = self.session.get(url, params=search_filters)
        response.raise_for_status()
        return response.json()

    def search_for_instances(self, search_filters: Dict = {}) -> List[Dict]:
        url = f"{self.rs_endpoint}/instances"
        response = self.session.get(url, params=search_filters)
        response.raise_for_status()
        return response.json()
