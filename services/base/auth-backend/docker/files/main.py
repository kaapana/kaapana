from fastapi import FastAPI
from fastapi import Response, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse

from init import error_page, logger
import uvicorn
import jwt
import requests

app = FastAPI()


def check_endpoint(access_token, requested_prefix):
    input = {
        "input": {"access_token": access_token, "requested_prefix": requested_prefix}
    }
    url = "http://open-policy-agent-service.services.svc:8181/v1/data/httpapi/authz"
    r = requests.post(
        url,
        json=input,
    )
    allow = r.json().get("result", {}).get("allow", False)
    return allow


@app.get("/auth-check", status_code=status.HTTP_200_OK)
async def auth_check(request: Request, response: Response):
    """
    Check if the user who made the request is mapped to the required roles in order to be authorized to access the requested resource.
    """

    requested_prefix = request.headers.get("x-forwarded-prefix")
    if requested_prefix is None:
        requested_prefix = request.headers.get("x-forwarded-uri")

    access_token = request.headers.get("x-forwarded-access-token", None)

    if access_token is None:
        decoded_access_token = {}
    else:
        decoded_access_token = jwt.decode(
            access_token, options={"verify_signature": False}
        )

    if check_endpoint(decoded_access_token, requested_prefix):
        message = f"Policies satisfied for {requested_prefix} -> ok"
        logger.warn(message)
        response.status_code = status.HTTP_200_OK
        return message
    else:
        message = f"No policy satisfied -> restricting access to {requested_prefix}"
        logger.info(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)


@app.get("/opa-bundles/{somedir}/{bundle}")
async def get_opa_bundles(somedir: str, bundle: str):
    """
    Return init data and policies as gzipped tarball.
    """
    f = open(f"/kaapana/app/{somedir}/{bundle}", "rb")
    return StreamingResponse(content=f, media_type="application/octet-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
