import httpx
from app.auth import get_external_token
from app.utils import wado_endpoint_url
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from kaapanapy.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


async def stream_wado(request: Request, token: str):
    """Stream the instance from the DICOMWeb server.

    Yields:
        bytes: DICOM instance
    """
    # Retrieve the base WADO URI endpoint from the request
    rs_endpoint = wado_endpoint_url(request)
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            f"{rs_endpoint}/wado",  # Adjust the endpoint as needed
            params=request.query_params,
            headers={"Authorization": f"Bearer {token}", **dict(request.headers)},
        ) as response:
            response.raise_for_status()  # Raise if any HTTP error occurs
            async for chunk in response.aiter_bytes():
                yield chunk


@router.get("/wado", tags=["WADO-URI"])
async def retrieve_instance(request: Request):
    """This endpoint streams the DICOM instance from WADO-URI server.

    Args:
        request (Request): Request object

    Returns:
        StreamingResponse: Response object
    """
    try:
        # Get Google OAuth token using the request object
        token = await get_external_token(request)

        # Stream the DICOM instance from the server
        return StreamingResponse(stream_wado(request=request, token=token))

    except httpx.HTTPStatusError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        return StreamingResponse(content=b"Failed to stream the instance.", status_code=http_err.response.status_code)

    except Exception as e:
        logger.error(f"An error occurred while streaming the instance: {e}")
        return StreamingResponse(content=b"Internal server error", status_code=500)
