import logging
import os
from typing import List

import requests
from kaapanapy.helper import get_project_user_access_token
from kaapanapy.settings import OpensearchSettings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CustomHelperDcmWeb:
    """
    Helper class for making authorized requests against a dicomweb server.
    """

    def __init__(
        self,
        access_token: str = None,
    ):
        """Initialize the HelperDcmWeb class.

        Args:
            access_token (str, optional): The access token of the user. Defaults to None.
        """

        try:
            # Local Operators
            from kaapana.blueprints.kaapana_global_variables import (
                DICOM_WEB_SERVICE_RS,
                DICOM_WEB_SERVICE_URI,
            )

            self.dcmweb_rs_endpoint = DICOM_WEB_SERVICE_RS
            self.dcmweb_uri_endpoint = DICOM_WEB_SERVICE_URI
        except:
            # Processing-Containers
            self.dcmweb_rs_endpoint = os.getenv("DICOM_WEB_SERVICE_RS")
            self.dcmweb_uri_endpoint = os.getenv("DICOM_WEB_SERVICE_URI")

        logger.debug(
            f"HelperDcmWeb initialized with service: {self.dcmweb_rs_endpoint}"
        )

        self.access_token = access_token or get_project_user_access_token()
        self.auth_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "x-forwarded-access-token": self.access_token,
        }

        self.session = requests.Session()
        self.session.headers.update(self.auth_headers)

        # For Multiplexer
        self.project_headers = {"project_index": OpensearchSettings().default_index}
        self.session.headers.update(self.project_headers)

    def get_studies(self, dcmweb_endpoint: str = None) -> List[dict]:
        headers = {"X-Endpoint-URL": dcmweb_endpoint} if dcmweb_endpoint else None
        url = f"{self.dcmweb_rs_endpoint}/studies"
        r = self.session.get(url, headers=headers)
        if r.status_code == 204:
            return []
        elif r.status_code == 404:
            return None
        else:
            r.raise_for_status()
            return r.json()

    def get_series_of_study(
        self, study_uid: str, dcmweb_endpoint: str = None
    ) -> List[dict]:
        headers = {"X-Endpoint-URL": dcmweb_endpoint} if dcmweb_endpoint else None
        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series"
        r = self.session.get(url, headers=headers)
        if r.status_code == 204:
            return []
        elif r.status_code == 404:
            return None
        else:
            r.raise_for_status()
            return r.json()

    def get_instances_of_series(
        self, study_uid: str, series_uid: str, dcmweb_endpoint: str = None
    ) -> List[dict]:

        headers = {"X-Endpoint-URL": dcmweb_endpoint} if dcmweb_endpoint else None

        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances"
        response = self.session.get(url, headers=headers)
        if response.status_code == 204:
            return []
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
            return response.json()

    def get_instance_metadata(
        self,
        study_uid: str,
        series_uid: str,
        instance_uid: str,
        dcmweb_endpoint: str = None,
    ) -> List[dict]:
        headers = {"X-Endpoint-URL": dcmweb_endpoint} if dcmweb_endpoint else None

        url = f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/metadata"
        response = self.session.get(url, headers=headers)
        if response.status_code == 204:
            return []
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
            return response.json()
