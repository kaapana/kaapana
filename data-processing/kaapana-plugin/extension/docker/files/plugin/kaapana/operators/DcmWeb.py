import time
from abc import ABC
from pathlib import Path
from typing import Dict, Optional

from kaapanapy.logger import get_logger
from requests import Response

logger = get_logger(__file__)


class DcmWebException(Exception):
    pass


class DcmWeb(ABC):
    def __init__(self, dcmweb_endpoints, session, client):
        self.dcmweb_endpoints = dcmweb_endpoints

        # Preffered
        self.session = session

        # Alternative: Only used to simplify store transaction
        # Using in WADO-RS was often missing an error message
        self.client = client

    @staticmethod
    def get_dcmweb_helper(
        dcmweb_endpoint: str,
        application_entity: str = "KAAPANA",
        service_account_info: Dict[str, str] = None,
    ):
        if "google" in dcmweb_endpoint:
            from DcmWebGcloudHelper import DcmWebGcloudHelper

            return DcmWebGcloudHelper(
                dcmweb_endpoint=dcmweb_endpoint,
                service_account_info=service_account_info,
            )
        elif "dcm4chee" in dcmweb_endpoint:
            from DcmWebLocalHelper import DcmWebLocalHelper

            return DcmWebLocalHelper(application_entity=application_entity)
        else:
            from DcmWebLocalHelper import DcmWebLocalHelper

            logger.error(f"Unknown dcmweb_endpoint: {dcmweb_endpoint}")
            logger.error("Defaulting to the local dcm4chee")
            return DcmWebLocalHelper(application_entity=application_entity)

    def check_reachability(self) -> bool:
        response = self.search_for_series()
        exception = None
        for i in range(10):
            try:
                response.raise_for_status()
                return True
            except Exception as e:
                exception = e
                logger.error(f"Connecting to pacs failed: {e}. Retry {i}")

        logger.error(
            f"Dcm web endpoint: {self.dcmweb_endpoints['rs']} is not available or wrong credentials. {exception}"
        )
        return False

    def check_if_series_in(self, series_uid: str) -> bool:
        for attempt in range(1, 31):

            response = self.search_for_series({"SeriesInstanceUID": series_uid})
            if response.status_code == 200:
                return True
            else:
                logger.error(
                    f"Attempt {attempt}/30: Error checking for series {series_uid} in PACS."
                )
                logger.error(f"{response.text} (status code: {response.status_code})")

            time.sleep(2)

        logger.error(f"Series {series_uid} not found in PACS after 30 attempts.")
        return False

    def retrieve_series(
        self,
        series_uid: str,
        target_dir: Path,
        include_series_dir: Optional[bool] = False,
    ):
        response = self.search_for_series({"SeriesInstanceUID": series_uid})

        if response.status_code != 200:
            logger.error(f"Failed to request series UID: {series_uid}")
            logger.error(f"Status code: {response.status_code}")
            logger.error(f"Error details: {response.text}")
            return False

        object_uids = [
            (
                obj["0020000D"]["Value"][0],  # StudyInstanceUID
                obj["00080018"]["Value"][0],  # SOPInstanceUID
            )
            for obj in response.json()
        ]

        if include_series_dir:
            target_dir /= series_uid
        target_dir.mkdir(parents=True, exist_ok=True)

        for object_uid in object_uids:
            study_uid = object_uid[0]
            object_uid = object_uid[1]
            result = self.retrieve_object(
                study_uid=study_uid,
                series_uid=series_uid,
                object_uid=object_uid,
                target_dir=target_dir,
            )
            if not result:
                return False

        return True

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
        url = f"{self.dcmweb_endpoints['wado']}"
        response = self.session.get(url, params=payload)

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

    def search_instances_of_study(self, study_uid: str) -> Response:
        url = f"{self.dcmweb_endpoints['rs']}/studies/{study_uid}/instances"
        response = self.session.get(url)
        return response

    def search_instances_of_series(self, study_uid: str, series_uid: str) -> Response:
        url = f"{self.dcmweb_endpoints['rs']}/studies/{study_uid}/series/{series_uid}/instances"
        response = self.session.get(url)
        return response

    def search_series_of_study(self, study_uid: str) -> Response:
        url = f"{self.dcmweb_endpoints['rs']}/studies/{study_uid}/series"
        response = self.session.get(url)
        return response

    def search_for_series(self, search_filters: Dict = {}) -> Response:
        url = url = f"{self.dcmweb_endpoints['rs']}/series"
        response = self.session.get(url, params=search_filters)
        return response

    def search_for_instances(self, search_filters: Dict = {}) -> Response:
        url = url = f"{self.dcmweb_endpoints['rs']}/instances"
        response = self.session.get(url, params=search_filters)
        return response

    @staticmethod
    def decode_dcmweb_endpoint(dcmweb_endpoint: str):
        pass

    @staticmethod
    def encode_dcmweb_endpoint(decoded_dcmweb_endpoint: str):
        pass
