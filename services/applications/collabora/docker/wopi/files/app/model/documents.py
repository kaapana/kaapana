import datetime
import re
import logging
from typing import List
from dataclasses import dataclass
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi import HTTPException

import requests
import xml.etree.ElementTree as ET
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


class DocumentStore(Minio):
    """
    A class to provide MinIO objects as MinioDocuments and to read and write files from and to MinIO
    """

    def __init__(
        self,
        access_token: str = None,
    ):
        """
        :access_token: Access token that should be used for communication with minio.
        """
        if access_token:
            self.access_token = access_token
            access_key, secret_key, session_token = self.minio_credentials()
        else:
            access_key, secret_key, session_token = "kaapanaminio", "Kaapana2020", None

        self.doc_lookup = {}
        self.docs: list(MinioDocument) = []

        minio_url = f"minio-service.services.svc:9000"
        super().__init__(
            minio_url,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            secure=False,
        )

    def minio_credentials(self):
        url = f"http://minio-service.services.svc:9000?Action=AssumeRoleWithWebIdentity&WebIdentityToken={self.access_token}&Version=2011-06-15"
        r = requests.post(url)
        xml_response = r.text
        root = ET.fromstring(xml_response)
        credentials = root.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}Credentials"
        )
        access_key_id = credentials.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}AccessKeyId"
        ).text
        secret_access_key = credentials.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}SecretAccessKey"
        ).text
        session_token = credentials.find(
            ".//{https://sts.amazonaws.com/doc/2011-06-15/}SessionToken"
        ).text
        return access_key_id, secret_access_key, session_token

    ### Documents

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

    def find_documents(self, extension_list: List[str], ignore_regex: str = None):
        """
        Find all documents in MinIO with matching extension and not matching ignore_regex.
        Populate self.docs and self.doc_lookup
        """
        extension_list = [ext for ext in extension_list]
        buckets = self.list_buckets()
        docs = []
        ignore_re = re.compile(ignore_regex) if ignore_regex else None
        for bucket in buckets:
            objects = self.list_objects(bucket.name, recursive=True)
            for object in objects:
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
        self.docs = docs
        self.doc_lookup.clear()
        # Populate hash lookup
        for doc in self.docs:
            self.doc_lookup[self.get_file_id(doc.path)] = doc

    #### WOPI
    def get_document(self, file_id) -> FileResponse:
        """
        Return the file from MinIO by its id.
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        doc = self.doc_lookup.get(file_id)
        object = self.get_object(doc.bucket, doc.path, length=doc.size)
        return PlainTextResponse(object.data)

    def write(self, file_id, body):
        """
        Write a file to MinIO.
        """
        if file_id not in self.doc_lookup:
            raise HTTPException(404)
        doc = self.doc_lookup.get(file_id)
        data = io.BytesIO(body)
        return self.put_object(doc.bucket, doc.path, data=data, length=len(body))

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
