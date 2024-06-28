from pathlib import Path
from typing import Dict

from dicomweb_client.api import DICOMwebClient
from dicomweb_client.ext.gcp.uri import GoogleCloudHealthcareURL
from google.auth.transport import requests
from google.oauth2 import service_account
from kaapana.operators.DcmWeb import DcmWeb
from kaapanapy.logger import get_logger

logger = get_logger(__file__)


class DcmWebGcloudHelper(DcmWeb):
    def __init__(
        self,
        dcmweb_endpoint: str,
        service_account_info: Dict[str, str],
    ):
        self.dcmweb_endpoint = dcmweb_endpoint
        dcmweb_endpoints = {
            "rs": dcmweb_endpoint,
            "wado": dcmweb_endpoint,
        }
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        session = requests.AuthorizedSession(credentials=credentials)
        url = GoogleCloudHealthcareURL(
            project_id=dcmweb_endpoint.split("/")[5],
            location=dcmweb_endpoint.split("/")[7],
            dataset_id=dcmweb_endpoint.split("/")[9],
            dicom_store_id=dcmweb_endpoint.split("/")[11],
        )
        client = DICOMwebClient(url=str(url), session=session)

        super().__init__(dcmweb_endpoints, session, client)

    def retrieve_object(
        self,
        study_uid: str,
        series_uid: str,
        object_uid: str,
        target_dir: Path,
    ):

        url = f"{self.dcmweb_endpoints['wado']}/studies/{study_uid}/series/{series_uid}/instances/{object_uid}"

        headers = {"Accept": "application/dicom; transfer-syntax=*"}
        response = self.session.get(url, headers=headers)

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
