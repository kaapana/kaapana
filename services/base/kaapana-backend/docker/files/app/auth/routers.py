from fastapi import APIRouter
from fastapi import Response,Request,status
from .services import auth_role_mapping_dict, logger

router = APIRouter(tags = ["auth"])
@router.get("/auth-check",status_code=status.HTTP_200_OK)
async def auth_check(request: Request,response: Response):
    requested_prefix = request.headers.get('x-forwarded-prefix')
    if requested_prefix is None:
        requested_prefix = request.headers.get('x-forwarded-uri')
        
    if requested_prefix is None:
        logger.info("No HTTP_X_FORWARDED_PREFIX could be identified within the request -> restricting access.")
        response.status_code = status.HTTP_403_FORBIDDEN
        return "x-forwarded-prefix not found"

    auth_groups = request.headers.get('x-forwarded-groups').split(",")
    if auth_groups is None:
        logger.info("No x-forwarded-groups could be identified within the request -> restricting access.")
        response.status_code = status.HTTP_403_FORBIDDEN
        return "x-forwarded-groups not found"
    
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
        return f"No role specified for prefix: {requested_prefix}"
    
    else:
        for user_role in user_roles:
            if user_role in prefix_roles_allowed:
                response.status_code = status.HTTP_200_OK
                return f"User ({user_roles=}) has one of the allowed roles: {user_role} -> access granted"
        
        response.status_code = status.HTTP_403_FORBIDDEN
        return f"User ({user_roles=}) has not one of the allowed roles: {prefix_roles_allowed} -> access denied"
