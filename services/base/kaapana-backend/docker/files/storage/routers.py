from fastapi import APIRouter, Response, HTTPException, Depends
from datetime import datetime
from app.dependencies import get_minio
import json
import os
import socket

router = APIRouter(tags=["storage"])

@router.get('/buckets')
def listbuckets(minio=Depends(get_minio)):
    """Return List of Minio buckets
    """
    buckets = minio.list_buckets()
    data = []
    for bucket in buckets:
        data.append({
          'name':str(bucket.name),
          'creation_date': bucket.creation_date,
          'webui':f'https://{os.getenv("HOSTNAME")}/minio/{bucket.name}'
        })
    return data


@router.post('/buckets/{bucketname}')
def makebucket(bucketname: str, minio=Depends(get_minio)):
    """
    To Create a Bucket
    """    
    bucketname = bucketname.lower().strip()
    if minio.bucket_exists(bucketname):
        raise HTTPException(status_code=409, detail=f"Bucket {bucketname} already exists.")
    else:
        minio.make_bucket(bucketname)
        return {}


@router.get('/buckets/{bucketname}')
def listbucketitems(bucketname: str, minio=Depends(get_minio)):
    """
    To List  Bucket Items
    """   
    bucket_items = [] 
    bucketname =  bucketname.lower().strip()
    if minio.bucket_exists(bucketname):
        objects = minio.list_objects(bucketname,recursive=True)
        for obj in objects:
          bucket_items.append({
            'bucket_name': str(obj.bucket_name),
            'object_name': str(obj.object_name),
            'last_modified': obj.last_modified,
            'etag': obj.etag,
            'size': obj.size,
            'type': obj.content_type})      

        return bucket_items
    else:
      raise HTTPException(status_code=404, detail=f"Bucket {bucketname} does not exist")
        
@router.delete('/buckets/{bucketname}')
def removebucket(bucketname: str, minio=Depends(get_minio)):
    """
    To remove a bucket
    """    
    bucketname =  bucketname.lower().strip()

    if minio.bucket_exists(bucketname):
        objects = list(minio.list_objects(bucketname))
        if objects:
          raise HTTPException(status_code=409, detail=f"Bucket {bucketname} not empty")
        else:
          minio.remove_bucket(bucketname)
          return {}
    else:
        raise HTTPException(status_code=404, detail=f"Bucket {bucketname} does not exist")

