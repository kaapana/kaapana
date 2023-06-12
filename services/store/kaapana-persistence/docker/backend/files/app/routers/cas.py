from fastapi import APIRouter, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse

from app.services.cas import CAS, Import
from app.dependencies import get_cas

router = APIRouter()


@router.post("/single")
async def process_incomming_file(file: UploadFile, cas: CAS = Depends(get_cas)):
    i = Import(
        files=[await cas.store(file)],
    )
    # store_object("import", i)
    return i


@router.get("/{key}", response_class=FileResponse)
async def get(key: str, cas: CAS = Depends(get_cas)):
    return await cas.get(key)


@router.delete("/{key}", status_code=204)
async def get(key: str, cas: CAS = Depends(get_cas)):
    return await cas.delete(key)


@router.post("/")
async def process_incomming_files(files: list[UploadFile], cas: CAS = Depends(get_cas)):
    i = Import(
        files=[await cas.store(file) for file in files],
    )
    # store_object("import", i)
    return i
