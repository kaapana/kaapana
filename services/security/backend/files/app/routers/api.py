from fastapi import APIRouter, HTTPException, Request
from helpers.extension_availability import registered_extensions
from models.extension import ExtensionRegistration
from helpers.wazuh import WazuhAPIAuthenication
import httpx

api_prefix = "api"
router = APIRouter(prefix=f"/{api_prefix}")
wazuh_authentication = WazuhAPIAuthenication()

@router.get("/available-extensions")
def get_available_extensions():
    return {"extensions": registered_extensions.get_names()}

@router.put("/register-extension")
def put_register_extension(extension: ExtensionRegistration):
    registered_extensions.add(extension)

@router.get("/extension/wazuh/agent-installed")
def wazuh_agent_installed():
    wazuh_authentication.retrieve_token()
    bearer_token = wazuh_authentication.get_bearer_token()
    if bearer_token is None:
        raise HTTPException(status_code=401, detail="No authentication token for Wazuh available")

    result = httpx.get("https://security-wazuh-service.services.svc:55000/agents", verify=False, headers={"Authorization": bearer_token})
    print(result)
    data = result.json()["data"]
    total_agents = int(data["total_affected_items"])
    print(data)
    print(total_agents)
    return {"agent_installed": total_agents > 1} # API lists manager instance as agent, but we need an additional agent running on host machine

# get data dump from specific extension
#@router.get("/extension/{extension-name}")

# todo: make wazuh and stackrox specific apis and enable them once registration is made
# todo: find a way to encapsulate event_registrations and provider specific data

@router.get("/{full_path:path}")
def catch_all_api(request: Request, full_path:str):
    raise HTTPException(status_code=404, detail="API route not available")

