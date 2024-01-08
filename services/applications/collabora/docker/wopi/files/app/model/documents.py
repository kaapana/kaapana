import datetime
import hashlib
import re
import logging
import os

from typing import List
from pathlib import Path
from dataclasses import dataclass
from fastapi.responses import FileResponse
from fastapi import HTTPException

log = logging.getLogger("uvicorn.error")


@dataclass
class Document:
    path: str
    extension: str
    modification_time: datetime.datetime
    creation_time: datetime.datetime


class DocumentStore:
    def __init__(self, document_root: Path):
        self.document_root = document_root
        self.doc_lookup = {}
        self.docs: list(Document) = []

    def _file_id_to_path(func):
        def wrapper(self, file_id: str, *args, **kwargs):
            return func(self, *args, path=self.path(file_id), **kwargs)

        return wrapper

    def get_file_id(self, file_path: str):
        return hashlib.sha1(str(file_path).encode()).hexdigest()

    def path(self, file_id: str):
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        path = self.doc_lookup.get(file_id)
        return path

    def find_documents(self, extension_list: List[str], ignore_regex: str = None):
        files = []
        for ext in extension_list:
            files.extend(self.document_root.glob(f"**/*.{ext}"))

        ignore_re = re.compile(ignore_regex) if ignore_regex else None

        docs = []
        for file in files:
            if ignore_re and ignore_re.match(str(file)):
                continue
            stats = file.stat()
            docs.append(
                Document(
                    path=file.relative_to(self.document_root),
                    extension=file.suffix[1:],
                    creation_time=datetime.datetime.fromtimestamp(
                        stats.st_ctime
                    ),  # stats.st_birthtime),
                    modification_time=datetime.datetime.fromtimestamp(stats.st_mtime),
                )
            )
        self.docs = docs

        # Populate hash lookup
        self.doc_lookup.clear()
        for doc in self.docs:
            self.doc_lookup[self.get_file_id(doc.path)] = doc.path

    @_file_id_to_path
    def get_document(self, path: str):
        log.info("Retreiving document %s", path)
        return FileResponse(self.document_root / path)

    @_file_id_to_path
    def size(self, path: str):
        return os.path.getsize(self.document_root / path)

    @_file_id_to_path
    def filename(self, path: str):
        return (self.document_root / path).name

    @_file_id_to_path
    def writable(self, path: str):
        return True

    @_file_id_to_path
    def write(self, path: str, body):
        file_path = self.document_root / path
        if not file_path.exists():
            raise Exception(f"File {path} can not be overwritten, it does not exist!")

        with open(file_path, "wb") as fp:
            fp.write(body)
