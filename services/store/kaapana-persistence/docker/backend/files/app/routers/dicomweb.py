import httpx
from httpx import AsyncClient
from fastapi import Request, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from app.config import get_settings
from app.logger import get_logger, function_logger_factory

logger = get_logger(__name__)

router = APIRouter()


class ReverseProxy:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.HTTP_SERVER = AsyncClient(base_url=base_url)

    # Thanks to https://github.com/tiangolo/fastapi/issues/1788#issuecomment-1071222163
    async def _reverse_proxy(self, request: Request):
        # TODO remove replace
        url = httpx.URL(
            path=request.url.path.replace("persistence/dicomweb/qidors/", ""),
            query=request.url.query.encode("utf-8"),
        )
        logger.info("Relay request to {url} (base_url = {self.base_url})")
        rp_req = self.HTTP_SERVER.build_request(
            request.method,
            url,
            headers=request.headers.raw,
            content=await request.body(),
        )
        try:
            rp_resp = await self.HTTP_SERVER.send(rp_req, stream=True)
            return StreamingResponse(
                rp_resp.aiter_raw(),
                status_code=rp_resp.status_code,
                headers=rp_resp.headers,
                background=BackgroundTask(rp_resp.aclose),
            )
        except httpx.ConnectError as e:
            raise HTTPException(
                503, f"Could not connect to {e.request.url} becasue {e}"
            )


# https://www.dicomstandard.org/using/dicomweb/retrieve-wado-rs-and-wado-uri
# https://dicom.nema.org/dicom/2013/output/chtml/part18/sect_6.5.html
wado_proxy = ReverseProxy(get_settings().wado_base_url)
router.add_route("/wadors/{path:path}", wado_proxy._reverse_proxy, ["GET"])

# https://dicom.nema.org/medical/DICOM/2014a/output/chtml/part18/sect_6.7.html
qido_proxy = ReverseProxy(get_settings().quido_base_url)
router.add_route("/qidors/{path:path}", qido_proxy._reverse_proxy, ["GET"])

# https://www.dicomstandard.org/using/dicomweb/store-stow-rs
# https://dicom.nema.org/dicom/2013/output/chtml/part18/sect_6.6.html
stowrs_proxy = ReverseProxy(get_settings().stow_root_url)
router.add_route("/stowrs/{path:path}", stowrs_proxy._reverse_proxy, ["POST"])
