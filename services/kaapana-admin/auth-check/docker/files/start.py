from fastapi import FastAPI, Response,Request,status
import json
import uvicorn

auth_role_mapping_path = "/app/auth_role_mapping.json"

with open(auth_role_mapping_path) as f:
    auth_role_mapping_dict = json.load(f)

print(json.dumps(auth_role_mapping_dict, indent=4))

app = FastAPI()
tasks = {"foo": "Listen to the Bar Fighters"}

@app.get("/auth-check",status_code=status.HTTP_200_OK)
async def auth_check(request: Request,response: Response):
    requested_prefix = request.headers.get('x-forwarded-prefix')
    if requested_prefix is None:
        requested_prefix = request.headers.get('x-forwarded-uri')
        
    if requested_prefix is None:
        # app.logger.info("No HTTP_X_FORWARDED_PREFIX could be identified within the request -> restricting access.")
        print(request.headers)
        response.status_code = status.HTTP_403_FORBIDDEN
        return "x-forwarded-prefix not found"

    auth_groups = request.headers.get('x-forwarded-groups').split(",")
    if auth_groups is None:
        # app.logger.info("No x-forwarded-groups could be identified within the request -> restricting access.")
        print(request.headers)
        response.status_code = status.HTTP_403_FORBIDDEN
        return "x-forwarded-groups not found"
    
    user_roles = []
    for group in auth_groups:
        if "role:" in group:
            user_roles.append(group.split(":")[-1])

    role_needed = None
    for restricted_access_prefix in auth_role_mapping_dict.keys():
        if restricted_access_prefix in requested_prefix:
            role_needed = auth_role_mapping_dict[restricted_access_prefix]
            break

    if role_needed is None:
        response.status_code = status.HTTP_200_OK
        return f"No role specified for prefix: {requested_prefix}"
    
    elif role_needed in user_roles:
        response.status_code = status.HTTP_200_OK
        return f"User ({user_roles=}) has specified role: {role_needed} -> access granted"
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return f"User ({user_roles=}) has not the requred role: {role_needed} -> access denied"

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)