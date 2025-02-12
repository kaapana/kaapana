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
