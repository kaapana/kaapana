import requests

from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, Response, File, Header
from sqlalchemy.orm import Session




router = APIRouter()


@router.get("/")
async def root(request: Request):
    return {"message": "Hello World updating", "root_path": request.scope.get("root_path")}

@router.get("/health-check")
async def health_check():
    return {f"Federated backend is up and running!"}