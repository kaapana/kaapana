from fastapi import FastAPI
from fastapi import Response,Request,status
from init import auth_role_mapping_dict, logger
import uvicorn

app = FastAPI()

@app.get("/auth-check",status_code=status.HTTP_200_OK)
async def auth_check(request: Request,response: Response):
    # for header, value in request.headers.items():
    #     logger.warn(f"{header}:{value}")
    requested_prefix = request.headers.get('x-forwarded-prefix')
    if requested_prefix is None:
        requested_prefix = request.headers.get('x-forwarded-uri')
        
    if requested_prefix is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No HTTP_X_FORWARDED_PREFIX could be identified within the request -> restricting access."
        logger.warn(message)
        return message

    user_requesting = request.headers.get('x-forwarded-preferred-username')
    if user_requesting is None:
        user_requesting = request.headers.get('x-forwarded-preferred-username')
        
    if user_requesting is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "'x-forwarded-preferred-username' could be identified within the request -> restricting access."
        logger.warn(message)
        return message

    auth_groups = request.headers.get('x-forwarded-groups').split(",")
    if auth_groups is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        message = "No x-forwarded-groups could be identified within the request -> restricting access."
        logger.warn("No x-forwarded-groups could be identified within the request -> restricting access.")
        return message
    
    user_roles = []
    for group in auth_groups:
        if "role:" in group:
            user_roles.append(group.split(":")[-1])

    prefix_roles_allowed = None
    for restricted_access_prefix in auth_role_mapping_dict.keys():
        if restricted_access_prefix in requested_prefix:
            prefix_roles_allowed = auth_role_mapping_dict[restricted_access_prefix]
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
                message = f"User {user_requesting}: access granted for: {requested_prefix}"
                logger.warn(message)
                return message
        
        response.status_code = status.HTTP_403_FORBIDDEN
        message = f"User ({user_roles=}) has not one of the allowed roles: {prefix_roles_allowed} -> access denied"
        logger.warn(message)
        return message

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)