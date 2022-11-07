import os
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.routing import Mount as Mount 
from pydantic import BaseModel

# todo: split everything into files

api_prefix = "api"
registered_extensions = []

class ExtensionRegistration(BaseModel):
    name: str
    url: str

#app = FastAPI(root_path=os.getenv('APPLICATION_ROOT', '/security'))

api_router = APIRouter(prefix=f"/{api_prefix}")

@api_router.get("/test")
def test():
    return {"Hello": "World"}

@api_router.get("/available-extensions")
def get_available_extensions():
    return {"extensions": ["Wazuh", "StackRox"]}
    # todo: check which extensions are still available?
    # return registered_extensions

@api_router.get("/container-issues")
def get_container_issues():
    return ""

@api_router.put("/register-extension")
def put_register_extension(extension: ExtensionRegistration):
    # check if extension.url is available, if so:
    registered_extensions += [extension]

# todo: delete / unregister extension method


security_routes = [
    Mount("/", StaticFiles(directory="./static/", html=True), name="vue-frontend")
]

security_app = FastAPI(routes=security_routes)
security_app.include_router(api_router)


# templates = Jinja2Templates(directory="./static/")

# @security_app.get("/{full_path:path}")
# def catch_all(request: Request, full_path: str):
#     print(full_path)
#     if full_path.startswith(api_prefix):
#         raise HTTPException(status_code=404)
#     else:
#         print(request)
#         return templates.TemplateResponse("index.html", {"request": request})

routes = [
    Mount("/security", security_app),
    Mount("/security/{full_path:path}", security_app),
]

app = FastAPI(routes=routes)
