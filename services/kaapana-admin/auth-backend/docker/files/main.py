from fastapi import FastAPI
from fastapi import Response, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse

from init import error_page, logger
import uvicorn
import jwt
import requests
import os
import json

app = FastAPI()


def check_endpoint(input: dict):
    """
    Send the decoded access token and requested prefex to the open policy agent.
    Return the decision of the open policy agent.
    """
    ADMIN_NAMESPACE = os.getenv("ADMIN_NAMESPACE")

    url = f"http://open-policy-agent-service.{ADMIN_NAMESPACE}.svc:8181/v1/data/httpapi/authz/allow"
    r = requests.post(
        url,
        json=input,
    )

    try:
        result = r.json()["result"]
    except KeyError as e:
        raise KeyError("No result from open policy agent")
    return result


@app.get("/auth-check")
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

    method = request.headers.get("x-forwarded-method")
    input = {
        "input": {
            "access_token": decoded_access_token,
            "requested_prefix": requested_prefix,
            "method": method,
        }
    }
    try:
        project_name = request.cookies.get("Project-Name", None)
        logger.debug(f"{project_name=}")
        aii_response = requests.get(
            f"http://aii-service.services.svc:8080/projects/{project_name}"
        )
        project = aii_response.json()
        input["input"]["project"] = project
    except requests.exceptions.ConnectionError as e:
        logger.debug(f"Could not fetch the project information from aii: {e}")

    if check_endpoint(input):
        message = f"Policies satisfied for {method} {requested_prefix} -> ok"
        logger.debug(message)
        response.status_code = status.HTTP_200_OK
        if input["input"].get("project"):
            response.headers["Project"] = json.dumps(project)
        return message
    else:
        message = f"No policy satisfied -> restricting access to {requested_prefix}"
        logger.warning(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)


@app.get("/opa-bundles/{somedir}/{bundle}")
async def get_opa_bundles(somedir: str, bundle: str):
    """
    Return init data and policies as gzipped tarball.
    """
    f = open(f"/kaapana/app/{somedir}/{bundle}", "rb")
    return StreamingResponse(content=f, media_type="application/octet-stream")


if __name__ == "__main__":
    ### Production
    uvicorn.run(app, host="0.0.0.0", port=8000)

    ### Development
    # uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
