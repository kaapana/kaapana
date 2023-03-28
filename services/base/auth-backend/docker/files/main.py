from fastapi import FastAPI
from fastapi import Response,Request,status
from fastapi.responses import HTMLResponse

from init import auth_role_mapping_dict,error_page, logger
import uvicorn
import jwt

app = FastAPI()

@app.get("/auth-check",status_code=status.HTTP_200_OK)
async def auth_check(request: Request,response: Response):
    """
    Check if the user who made the request is mapped to the required roles in order to be authorized to access the requested resource.
    """
    # for header, value in request.headers.items():
    #     logger.warn(f"{header}:{value}")
    requested_prefix = request.headers.get('x-forwarded-prefix')
    if requested_prefix is None:
        requested_prefix = request.headers.get('x-forwarded-uri')

    for url_auth_config in auth_role_mapping_dict.keys():
        if url_auth_config.startswith(requested_prefix) and auth_role_mapping_dict[url_auth_config] == "whitelisted":
            message = f"White-listed auth-endpoint: {requested_prefix} -> ok"
            logger.warn(message)
            response.status_code = status.HTTP_200_OK
            return message
    
    if requested_prefix is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No HTTP_X_FORWARDED_PREFIX could be identified within the request -> restricting access."
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)

    access_token = request.headers.get('x-forwarded-access-token')
    if access_token is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No x-forwarded-access-token could be identified within the request -> restricting access."
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)

    decoded_access_token = jwt.decode(access_token, options={"verify_signature": False})
    realm_access = decoded_access_token.get("realm_access", {"roles": []})
    user_roles = realm_access["roles"]

    user_requesting = decoded_access_token.get("preferred_username", None)
    if user_requesting is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No 'preferred_username' could be identified within the access token -> restricting access."
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)

    prefix_roles_allowed = None
    for url_auth_config in auth_role_mapping_dict.keys():
        if url_auth_config in requested_prefix:
            prefix_roles_allowed = auth_role_mapping_dict[url_auth_config]
            break

    if prefix_roles_allowed is None:
        response.status_code = status.HTTP_200_OK
        message = f"No role specified for prefix: {requested_prefix}"
        logger.warn(message)
        return message
    
    else:
        for user_role in user_roles:
            if user_role in prefix_roles_allowed:
                response.status_code = status.HTTP_200_OK
                message = f"User {user_requesting}: Access granted for: {requested_prefix}"
                logger.warn(message)
                return message
        
        response.status_code = status.HTTP_403_FORBIDDEN
        message = f"User ({user_roles=}) has not one of the allowed roles: {prefix_roles_allowed} -> access denied"
        logger.warn(message)
        return HTMLResponse(content=error_page, status_code=status.HTTP_403_FORBIDDEN)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)