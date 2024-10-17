import traceback

import httpx
from app.auth import get_external_token
from app.logger import get_logger
from app.utils import rs_endpoint_url
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = get_logger(__file__)


async def fetch_thumbnail_async(url: str, token: str) -> StreamingResponse:
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "image/png"
        }
        async def stream_thumbnail():    
            async with httpx.AsyncClient() as client:
                async with client.stream(method="GET", url=url, headers=headers, timeout=10) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_thumbnail())
    
    except httpx.HTTPStatusError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        logger.error(f"Status code: {http_err.response.status_code}")
        return Response(content="Could not retrieve thumbnail", status_code=http_err.response.status_code)
    except Exception as e:
        logger.error("Download of thumbnail was not successful")
        logger.error(f"URL: {url}")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(content="Could not retrieve thumbnail", status_code=404)


async def fetch_instances_async(url: str, token: str) -> str:
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/dicom+json"
        }

        # Using async httpx client to fetch the instances
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            instances = response.json()

            # Sorting to find the middle instance
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
        return None


@router.get("/studies/{study}/series/{series}/instances/{instance}/thumbnail")
async def retrieve_instance_thumbnail(
    study: str,
    series: str,
    instance: str,
    request: Request,
):
    """Retrieve a specific instance thumbnail"""
    try:
        # Get Google OAuth token
        token = await get_external_token(request)

        # Construct the URL for fetching the thumbnail
        rs_endpoint = rs_endpoint_url(request)
        url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/rendered"

        # Fetch and return the thumbnail
        return await fetch_thumbnail_async(url, token)
    
    except Exception as e:
        logger.error("Error while retrieving instance thumbnail")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(content="Internal server error", status_code=500)


@router.get("/studies/{study}/series/{series}/thumbnail")
async def retrieve_series_thumbnail(
    study: str,
    series: str,
    request: Request,
):
    """Retrieve the thumbnail of the middle instance in a series"""
    try:
        # Get Google OAuth token
        token = await get_external_token(request)

        # Construct the URL for fetching the instances
        rs_endpoint = rs_endpoint_url(request)
        url = f"{rs_endpoint}/studies/{study}/series/{series}/instances"

        # Fetch the middle instance UID
        instance = await fetch_instances_async(url, token)
        if not instance:
            return Response(
                content="Couldn't find middle slice. Aborting downloading thumbnail ... ",
                status_code=404,
            )

        # Fetch and return the thumbnail for the middle instance
        thumbnail_url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/rendered"
        return await fetch_thumbnail_async(thumbnail_url, token)
    
    except Exception as e:
        logger.error("Error while retrieving series thumbnail")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(content="Internal server error", status_code=500)
