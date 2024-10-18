from app.logger import get_logger
from fastapi import APIRouter, Request, Response

router = APIRouter()
logger = get_logger(__file__)


@router.get("/endpoints", tags=["CUSTOM"])
async def endpoints(request: Request, session):
    # TODO Return list of all endpoints
    return Response("Not implemented")

@router.get("/endpoint/{endpoint}", tags=["CUSTOM"])
async def endpoint(request: Request, session):
    # TODO return information about this endpoint (from the secret)
    return Response("Not implemented")

@router.post("/endpoint/{endpoint}", tags=["CUSTOM"])
async def endpoint(request: Request):
    # TODO add new endpoint 
    return Response("Not implemented")