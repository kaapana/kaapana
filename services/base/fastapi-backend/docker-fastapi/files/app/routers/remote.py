from typing import Optional, List
import requests
import json
from fastapi import APIRouter, UploadFile, Response, File, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db

from app import models
from app import crud
from app import schemas
from app import utils


router = APIRouter()


@router.get("/health-check")
async def health_check():
    return {f"Federated backend is up and running!"}


@router.get("/datasets")
async def datasets():
    return utils.get_dataset_list()


@router.get("/minio-presigned-url")
async def minio_presigned_url(presigned_url: str = Header(...)):
    print(f'http://minio-service.store.svc:9000{presigned_url}')
    resp = requests.get(f'http://minio-service.store.svc:9000{presigned_url}')
    # excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    return Response(resp.content, resp.status_code)


@router.post("/minio-presigned-url")
def minio_presigned_url(file: UploadFile = File(...), presigned_url: str = Header(...)):
    resp = requests.put(
        f'http://minio-service.store.svc:9000{presigned_url}', data=file.file)
    # excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    # headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    # print(resp)
    response = Response(resp.content, resp.status_code)
    return response
