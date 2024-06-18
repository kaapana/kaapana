from fastapi import APIRouter, Request
from ..proxy_request import proxy_request

router = APIRouter()


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(request: Request):
    return await proxy_request(request, "/studies", "POST")


@router.post("/studies/{study}", tags=["STOW-RS"])
async def store_instances_in_study(study: str, request: Request):
    return await proxy_request(request, f"/studies/{study}", "POST")
