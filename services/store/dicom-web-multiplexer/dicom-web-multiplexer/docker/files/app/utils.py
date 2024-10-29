from app.config import DICOMWEB_BASE_URL
from app.logger import get_logger
from fastapi.datastructures import URL

logger = get_logger(__name__)


def dicom_web_filter_url(request: URL) -> str:
    return DICOMWEB_BASE_URL + str(request.url).split("dicom-web-filter")[-1]


def wado_endpoint_url(request: URL) -> str:
    dcmweb_endpoint = request.state.endpoint
    if "google" in dcmweb_endpoint:
        return f"{dcmweb_endpoint}/dicomWeb"
    else:
        raise NotImplementedError(f"Not supported endpoint: {dcmweb_endpoint}")


def rs_endpoint_url(request: URL) -> str:
    dcmweb_endpoint = request.state.endpoint
    if "google" in dcmweb_endpoint:
        return f"{dcmweb_endpoint}/dicomWeb"
    else:
        raise NotImplementedError(f"Not supported endpoint: {dcmweb_endpoint}")
    
    