from fastapi import APIRouter
import httpx

router = APIRouter(prefix=f"/tests")

@router.get("/ping-wazuh")
async def ping_wazuh():
    result = await httpx.get("https://security-wazuh-service.services.svc:55000/")
    print(result)
    return result.text

@router.get("/")
def test():
    return {"Hello": "World"}
