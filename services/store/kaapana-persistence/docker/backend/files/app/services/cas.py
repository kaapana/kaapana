import magic
import pathlib
import hashlib

from pydantic import BaseModel
from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse
from typing import BinaryIO


class ImportFile(BaseModel):
    filename: str
    mime_type: str
    mime_type_derived: str
    cas_key: str
    size: int


class Import(BaseModel):
    files: list[ImportFile] = []


class CAS:
    BUF_SIZE = 65536

    def __init__(self, root_path: str):
        self.data_root = pathlib.Path(root_path)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.mime = magic.Magic(mime=True)

    async def store(self, file: BinaryIO) -> ImportFile:
        sha1 = hashlib.sha1()

        # file.content_type is application/octet-stream therfore the derived mime type is often more exact
        derived_mime = magic.from_buffer(await file.read(self.BUF_SIZE), mime=True)
        await file.seek(0)

        while True:
            data = await file.read(self.BUF_SIZE)
            if not data:
                break
            sha1.update(data)
        key = str(sha1.hexdigest())

        file_path = self.data_root / key
        if not file_path.exists():
            await file.seek(0)
            with open(file_path, "wb+") as fp:
                fp.write(await file.read())

        imported_file = ImportFile(
            filename=file.filename,
            mime_type=file.content_type if file.content_type else "",
            mime_type_derived=derived_mime,
            cas_key=key,
            size=file.size,
        )
        # store_object("imported_file", imported_file)
        return imported_file

    async def get_mime(self, key: str):
        file_path = self.data_root / key
        with open(file_path, "rb") as fp:
            derived_mime = magic.from_buffer(fp.read(self.BUF_SIZE), mime=True)
        return derived_mime

    async def get(self, key: str) -> FileResponse:
        file_path = self.data_root / key
        if file_path.exists():
            # Querying for original mimetype via the import file is also possible
            with open(file_path, "rb") as fp:
                derived_mime = magic.from_buffer(fp.read(self.BUF_SIZE), mime=True)

            # TODO use stream response instead of opening to file handlers
            return FileResponse(file_path, media_type=derived_mime)
        else:
            raise HTTPException(
                status_code=404, detail=f"Key {key} not found in storage"
            )

    async def delete(self, key: str):
        file_path = self.data_root / key
        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Key {key} not found in storage"
            )
        file_path.unlink()
