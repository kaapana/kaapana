from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.services.urn_dispatcher import URNDispatcher
from app.dependencies import get_dispatcher_service

router = APIRouter()


@router.get("/dispatchers")
async def get(dispatcher_service: URNDispatcher = Depends(get_dispatcher_service)):
    return dispatcher_service.resolvers


@router.get("/{urn}/viewer", response_class=RedirectResponse)
async def get(
    urn: str,
    dispatcher_service: URNDispatcher = Depends(get_dispatcher_service),
    settings: Settings = Depends(get_settings),
):
    viewer_link = await dispatcher_service.get_viewer_link(urn)
    if not viewer_link:
        return RedirectResponse(f"{settings.base_url}/urn/{urn}")
    else:
        return viewer_link


@router.get("/{urn}")
async def get(
    urn: str, dispatcher_service: URNDispatcher = Depends(get_dispatcher_service)
):
    return await dispatcher_service.get(urn)


@router.put("/{urn}")
async def put(
    urn: str,
    request: Request,
    dispatcher_service: URNDispatcher = Depends(get_dispatcher_service),
):
    return await dispatcher_service.put(urn, request.body())


@router.delete("/{urn}")
async def delete(
    urn: str, dispatcher_service: URNDispatcher = Depends(get_dispatcher_service)
):
    return await dispatcher_service.delete(urn)
