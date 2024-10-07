from fastapi import Request
from kaapanapy.helper import get_opensearch_client
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from app.logger import get_logger

logger = get_logger(__name__)


def get_endpoint(request: Request):
    if "series" in str(request.url):
        url_parts = str(request.url).split("/")
        # study_uid = url_parts[url_parts.index("studies") + 1]
        series_uid = url_parts[url_parts.index("series") + 1]
        user_access_token = request.headers["x-forwarded-access-token"]
        dcm_uid_objects = HelperOpensearch.get_dcm_uid_objects(series_instance_uids=[series_uid], access_token=user_access_token)
        endpoint = dcm_uid_objects[0]["dcm-uid"]["source_presentation_address"]
        if endpoint is None:
            return "local"
        else:
            return endpoint
    else:
        return "local"