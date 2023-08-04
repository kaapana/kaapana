from fastapi import APIRouter, Depends, HTTPException, Request, Body, Query
from urnparse import InvalidURNFormatError

from app.services.schema import SchemaService
from app.dependencies import get_schema_service

router = APIRouter()


@router.get("/")
async def get_schemas(
    include_version: bool = Query(
        False, description="If true includes version suffix for each schema"
    ),
    schema_service: SchemaService = Depends(get_schema_service),
):
    return [schema_urn async for schema_urn in schema_service.list(include_version)]


@router.get("/{urn}", summary="Get schemas")
async def get(
    urn: str,
    all_versions: bool = Query(
        False,
        description="If true all versions of the schema a returned, otherwise only the latest version is returned",
    ),
    schema_service: SchemaService = Depends(get_schema_service),
):
    return dict(
        [(x["version"], x) async for x in schema_service.get(urn, all_versions)]
    )


@router.get("/{urn}/versions", summary="Get versions of a specific schema")
async def versions(
    urn: str, schema_service: SchemaService = Depends(get_schema_service)
):
    return [version async for version in schema_service.versions(urn)]


@router.get("/{urn}/latest_version", summary="Get latest version for a schema")
async def versions(
    urn: str, schema_service: SchemaService = Depends(get_schema_service)
):
    return await schema_service.latest_version(urn)


@router.post("/", summary="Register a new schema or a new version of a schema")
async def register(
    schema_dict: dict = Body(...),
    exist_ok: bool = Query(
        False, description="Fail if schema already exist in given version"
    ),
    schema_service: SchemaService = Depends(get_schema_service),
):
    return await schema_service.register(schema_dict, exist_ok)


@router.delete(
    "/{urn}",
    status_code=204,
    summary="Delete a specific version or all versions of a schema",
)
async def delete(
    urn: str,
    schema_service: SchemaService = Depends(get_schema_service),
):
    if not await schema_service.delete(urn):
        raise HTTPException(404, f"Schema {urn} was not found!")


@router.get(
    "/{urn}/synthetic-data", summary="Generate synthetic dummy data for a given schema"
)
async def get_syntectic_data(
    urn: str,
    count: int = Query(10, description="Number of objects to generate"),
    schema_service: SchemaService = Depends(get_schema_service),
):
    return await schema_service.generate(urn, count)
