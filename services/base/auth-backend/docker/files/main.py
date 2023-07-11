import re
import uvicorn
import jwt
import jinja2

from fastapi import FastAPI
from fastapi import Response, Request, status
from fastapi.responses import HTMLResponse

from init import auth_role_mapping_dict, error_page, logger

app = FastAPI()

jinja_environment = jinja2.Environment()


@app.get("/auth-check", status_code=status.HTTP_200_OK)
async def auth_check(request: Request, response: Response):
    """
    Check if the user who made the request is mapped to the required roles in order to be authorized to access the requested resource.
    """
    # for header, value in request.headers.items():
    #     logger.warn(f"{header}:{value}")
    requested_prefix = request.headers.get("x-forwarded-prefix")
    if requested_prefix is None:
        requested_prefix = request.headers.get("x-forwarded-uri")

    access_token = request.headers.get("x-forwarded-access-token")

    decoded_access_token = (
        jwt.decode(access_token, options={"verify_signature": False})
        if access_token
        else {}
    )
    realm_access = decoded_access_token.get("realm_access", {"roles": []})
    user_roles = realm_access["roles"]
    user_requesting = decoded_access_token.get("preferred_username", None)

    # reading infos from auth_role_mapping_dict
    roles_to_access_unkown_resources = auth_role_mapping_dict[
        "roles_to_access_unkown_resources"
    ]

    # Currently only used in Neurorad project
    role_mappings = {}
    for k, v in auth_role_mapping_dict["role_mapping"].items():
        template = jinja_environment.from_string(k)
        role_mappings[
            template.render(user_roles=user_roles, user_requesting=user_requesting)
        ] = v

    for url_auth_config in role_mappings.keys():
        pattern = re.compile(url_auth_config)
        if (
            pattern.match(requested_prefix)
            and "whitelisted" in role_mappings[url_auth_config]
        ):
            message = f"White-listed auth-endpoint: {requested_prefix} -> ok"
            logger.warn(message)
            response.status_code = status.HTTP_200_OK
            return message

    if requested_prefix is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No HTTP_X_FORWARDED_PREFIX could be identified within the request -> restricting access."
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)

    if access_token is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No x-forwarded-access-token could be identified within the request -> restricting access."
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)

    if user_requesting is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No 'preferred_username' could be identified within the access token -> restricting access."
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)

    prefix_roles_allowed = None
    for url_auth_config in role_mappings.keys():
        pattern = re.compile(url_auth_config)
        if pattern.match(requested_prefix):
            # Found a rule for the requested prefix
            prefix_roles_allowed = role_mappings[url_auth_config]
            break

    if prefix_roles_allowed:
        for user_role in user_roles:
            if user_role in prefix_roles_allowed:
                response.status_code = status.HTTP_200_OK
                message = (
                    f"User {user_requesting}: Access granted for: {requested_prefix}"
                )
                logger.warn(message)
                return message

        response.status_code = status.HTTP_403_FORBIDDEN
        message = f"User ({user_roles=}) has not one of the allowed roles: {prefix_roles_allowed} -> access denied"
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)
    else:
        for user_role in user_roles:
            if user_role in roles_to_access_unkown_resources:
                response.status_code = status.HTTP_200_OK
                message = f"No role specified for prefix: {requested_prefix}, but user is part of the 'roles_to_access_unkown_resources' -> access granted"
                logger.warn(message)
                return message

        response.status_code = status.HTTP_403_FORBIDDEN
        message = f"No role specified for prefix: {requested_prefix} and user is not part of the 'roles_to_access_unkown_resources' -> access denied"
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)


if __name__ == "__main__":
    # Only used in dev mode!
    uvicorn.run(app, host="0.0.0.0", port=8000)
