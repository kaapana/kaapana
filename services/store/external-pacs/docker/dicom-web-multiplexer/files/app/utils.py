from app.config import DICOMWEB_BASE_URL
from app.logger import get_logger
from fastapi.datastructures import URL

logger = get_logger(__name__)


def dicom_web_filter_url(request: URL) -> str:
    """Generates a filtered DICOMWeb URL based on the incoming request.

    Args:
        request (URL): The incoming request object containing the original URL.

    Returns:
        str: The filtered DICOMWeb URL, derived from the base URL and the request path.
    """
    logger.info(DICOMWEB_BASE_URL)
    logger.info(str(request.url))
    logger.info(str(request.url))
    return DICOMWEB_BASE_URL + str(request.url).split("dicom-web-filter")[-1]


def wado_endpoint_url(request: URL) -> str:
    """Generates the WADO-RS endpoint URL for DICOMWeb.

    Args:
        request (URL): The incoming request object containing the endpoint information.

    Returns:
        str: The WADO-RS endpoint URL for supported endpoints.

    Raises:
        NotImplementedError: If the endpoint is not supported.
    """
    dcmweb_endpoint = request.state.endpoint
    if "google" in dcmweb_endpoint:
        return f"{dcmweb_endpoint}/dicomWeb"
    else:
        raise NotImplementedError(f"Not supported endpoint: {dcmweb_endpoint}")


def rs_endpoint_url(request: URL) -> str:
    """Generates the QIDO-RS/RS endpoint URL for DICOMWeb.

    Args:
        request (URL): The incoming request object containing the endpoint information.

    Returns:
        str: The RS endpoint URL for supported endpoints.

    Raises:
        NotImplementedError: If the endpoint is not supported.
    """
    dcmweb_endpoint = request.state.endpoint
    if "google" in dcmweb_endpoint:
        return f"{dcmweb_endpoint}/dicomWeb"
    else:
        raise NotImplementedError(f"Not supported endpoint: {dcmweb_endpoint}")
