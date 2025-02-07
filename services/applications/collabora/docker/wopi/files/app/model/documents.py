import datetime
import re
import logging
from typing import List
from dataclasses import dataclass
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi import HTTPException
from minio import Minio
import base64
import io

log = logging.getLogger("uvicorn.error")


@dataclass
class MinioDocument:
    bucket: str
    path: str
    extension: str
    modification_time: datetime.datetime
    creation_time: datetime.datetime
    size: int


class DocumentStore:
    """
    A class to provide MinIO objects as MinioDocuments and to read and write files from and to MinIO
    """

    def __init__(
        self,
    ):
        self.doc_lookup = {}
        self.docs: list(MinioDocument) = []

    def _file_id_to_path(func):
        """
        Decorator to call a function with path from file_id
        """

        def wrapper(self, file_id: str, *args, **kwargs):
            return func(self, *args, path=self.path(file_id), **kwargs)

        return wrapper

    def get_file_id(self, file_path: str):
        """
        Return the base64 encoded file_path as the id
        """
        path_bytes = file_path.encode("ascii")
        base64_bytes = base64.b64encode(path_bytes)
        return base64_bytes.decode("ascii")

    def path(self, file_id: str):
        """
        Return path by file_id
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        path = self.doc_lookup.get(file_id)
        return path

    def find_documents(
        self, minio: Minio, extension_list: List[str], ignore_regex: str = None
    ):
        """
        Find all documents in MinIO with matching extension and not matching ignore_regex.
        Populate self.docs and self.doc_lookup
        """
        extension_list = [ext for ext in extension_list]
        docs = []
        ignore_re = re.compile(ignore_regex) if ignore_regex else None
        for bucket in minio.list_buckets():
            for object in minio.list_objects(bucket.name, recursive=True):
                extension = object.object_name.split(".")[-1]
                if extension not in extension_list or (
                    ignore_re and ignore_re.match(object.object_name)
                ):
                    continue
                docs.append(
                    MinioDocument(
                        path=object.object_name,
                        bucket=bucket.name,
                        extension=extension,
                        modification_time=object.last_modified,
                        creation_time=object.last_modified,
                        size=object.size,
                    )
                )
        log.info("Found %i documents", len(docs))
        self.docs = docs
        self.doc_lookup.clear()
        # Populate hash lookup
        for doc in self.docs:
            self.doc_lookup[self.get_file_id(doc.path)] = doc

    #### WOPI
    def get_document(self, minio: Minio, file_id) -> FileResponse:
        """
        Return the file from MinIO by its id.
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        doc = self.doc_lookup.get(file_id)
        object = minio.get_object(doc.bucket, doc.path, length=doc.size)
        return PlainTextResponse(object.data)

    def write(self, minio: Minio, file_id, body):
        """
        Write a file to MinIO.
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        doc = self.doc_lookup.get(file_id)
        data = io.BytesIO(body)
        return minio.put_object(doc.bucket, doc.path, data=data, length=len(body))

    def filename(self, file_id: str):
        """
        Return the name of a file given its id.
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        return self.doc_lookup.get(file_id).path

    def size(self, file_id):
        """
        Return the size of the file given its id.
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        return self.doc_lookup.get(file_id).size

    def writable(self, file_id):
        """
        Return whether the file is writable given its id.
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        return True
