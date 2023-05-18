from fastapi import APIRouter, Depends, Body, HTTPException, Request, Query, Path
from app.services.object import ObjectService
from app.dependencies import get_object_service

router = APIRouter()


@router.get("/{urn}", summary="Get all Objects for a specific schema")
async def get_all(
    urn: str, object_service: ObjectService = Depends(get_object_service)
):
    return [x async for x in object_service.get(urn)]


@router.post("/{urn}", summary="Store a new object")
async def store_object(
    urn: str = Path(
        ...,
        description="Schema urn for the new object, if no schema version is specified, the latest version will be used.",
    ),
    obj: dict = Body(...),
    skip_validation: bool = Query(
        False,
        description="If true the posted object will not get validated against the schema",
    ),
    object_service: ObjectService = Depends(get_object_service),
):
    return await object_service.store(obj, urn, skip_validation=skip_validation)


@router.delete(
    "/{urn}",
    status_code=204,
    summary="Delete an object in a specific version (if specified) or all version",
)
async def delete_object(
    urn: str,
    all_versions=Query(
        False, description="If true all versions of the object are deleted"
    ),
    object_service: ObjectService = Depends(get_object_service),
):
    if not await object_service.delete(urn, all_versions):
        raise HTTPException(404, f"Object {urn} was not found!")


@router.get("/{urn}/query", summary="Query for objects with specific values")
async def query_object(
    urn: str, req: Request, object_service: ObjectService = Depends(get_object_service)
):
    request_args = dict(req.query_params)
    return dict([x async for x in object_service.query(urn, request_args)])


# @router.get("/")
# def get_namespace():
#     return []


# @router.get("/{namespace}")
# def get_namespace_specific(namespace: str):
#     return []


# @router.get("/{namespace}/{nss}")
# def get_namespace_specific_version(namespace: str, nss: str):
#     return []


# @router.get("/{namespace}/{nss}/{version}")
# def get_namespace_specific_version_objects(namespace: str, nss: str, version: str):
#     return []


# @router.get("/{namespace}/{nss}/{version}/{idx}")
# def get_namespace_specific_version_objects(
#     namespace: str, nss: str, version: str, idx: str
# ):
#     return []
