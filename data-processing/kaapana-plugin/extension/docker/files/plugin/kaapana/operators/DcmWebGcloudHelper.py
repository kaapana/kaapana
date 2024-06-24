import json

from dicomweb_client.api import DICOMwebClient
from dicomweb_client.ext.gcp.uri import GoogleCloudHealthcareURL
from google.auth.transport import requests
from google.oauth2 import service_account
from kaapanapy.Clients.DcmWeb import DcmWeb
from kaapanapy.logger import get_logger

logger = get_logger(__file__)


class DcmWebGcloudHelper(DcmWeb):
    def __init__(
        self,
        dcmweb_endpoint: str,
        service_account_info: str,
    ):
        self.dcmweb_endpoint = dcmweb_endpoint
        dcmweb_endpoints = {
            "rs": dcmweb_endpoint,
            "wado": dcmweb_endpoint,
        }
        service_account_info = json.loads(service_account_info)
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
