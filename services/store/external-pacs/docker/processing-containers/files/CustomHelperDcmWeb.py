import logging

from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CustomHelperDcmWeb(HelperDcmWeb):
    """
    Helper class for making authorized requests against a DICOM Web multiplexer.
    """

    def __init__(self, dcmweb_endpoint: str, access_token: str = None):
        """Initialize the `CustomHelperDcmWeb` class.

        Args:
            access_token (str, optional): The access token of the user. If not provided,
                the access token is obtained from the project user access token.
            dcmweb_endpoint (str): The DICOM Web endpoint URL to set in the request headers. This is a required parameter.

        """
        super().__init__(access_token)
        self.session.headers.update({"X-Endpoint-URL": dcmweb_endpoint})
        self.dcmweb_endpoint = dcmweb_endpoint

    def get_instance_metadata(
        self,
        study_uid: str,
        series_uid: str,
        instance_uid: str,
    ):
        response = self.session.get(
            f"{self.dcmweb_rs_endpoint}/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/metadata"
        )
        response.raise_for_status()
        if response.status_code == 204:
            return []

        if response.status_code == 200:
            return response.json()
