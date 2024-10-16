import traceback

from app.auth import get_external_session
from app.logger import get_logger
from app.utils import rs_endpoint_url
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

router = APIRouter()

logger = get_logger(__file__)


def fetch_thumbnail(url, session) -> Response:
    try:
        headers = {"Accept": "image/png"}
        response = session.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return StreamingResponse(
            iter([response.content]),
            media_type="image/png",
        )
    except Exception as e:
        logger.error("Download of thumbnail was not successful")
        logger.error(f"URL: {url}")
        logger.error(f"Status code: {response.status_code}")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(content="Could not retrieve thumbnail", status_code=404)


def fetch_instances(url, session) -> str:
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        instances = response.json()
        instance = sorted(
            instances, key=lambda x: x.get("00200013", {"Value": [0]})["Value"][0]
        )[len(instances) // 2]
        object_uid = instance["00080018"]["Value"][0]
        return object_uid
    except Exception as ex:
        logger.error("Couldn't find middle slice. Aborting downloading thumbnail ... ")
        logger.error(f"URL: {url}")
        logger.error(ex)
        logger.error(traceback.format_exc())


# Supplement 203: Thumbnail Resources for DICOMweb
@router.get("/studies/{study}/series/{series}/instances/{instance}/thumbnail")
async def retrieve_instance_thumbnail(
    study: str,
    series: str,
    instance: str,
    request: Request,
):
    session = get_external_session(request)
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/rendered"

    return fetch_thumbnail(url, session)


@router.get("/studies/{study}/series/{series}/thumbnail")
async def retrieve_series_thumbnail(
    study: str,
    series: str,
    request: Request,
):
    session = get_external_session(request)
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}/series/{series}/instances"
    instance = fetch_instances(url, session)
    if not instance:
        return Response(
            content="Couldn't find middle slice. Aborting downloading thumbnail ... ",
            status_code=402,
        )

    url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/rendered"
    return fetch_thumbnail(url, session)
