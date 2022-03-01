from fastapi import APIRouter, Response, HTTPException
from minio import Minio
from datetime import datetime
import json
import os
import socket

router = APIRouter(tags=["storage"])

def get_minio_client():
  # TODO move minio initalization in a more general place, and reuse existing client in subsequent endpoints
  _minio_url=os.getenv('MINIO_URL')
  _minio_access_key = os.getenv('MINIO_ACCESS_KEY')
  _minio_secret_key = os.getenv('MINIO_SECRET_KEY')

  if not _minio_url:
    print('Minio: no url provided')
    return None

  if not _minio_access_key:
    print('Minio: no access key provided')
    return None

  if not _minio_secret_key:
    print('Minio: no secret key provided')
    return None

  print(f"Minio url: {_minio_url}")
  #Initializing Minio Client
  return Minio(_minio_url,
    access_key=_minio_access_key,
    secret_key=_minio_secret_key,
    secure=False)

minioClient = get_minio_client()


@router.get('/buckets')
def listbuckets():
    """Return List of Minio buckets
    """
    buckets = minioClient.list_buckets()
    data = []
    for bucket in buckets:
        data.append({
          'name':str(bucket.name),
          'creation_date': bucket.creation_date,
          'webui':f'https://{os.getenv("HOSTNAME")}/minio/{bucket.name}'
        })
    return data


@router.post('/buckets/{bucketname}')
def makebucket(bucketname: str):
    """
    To Create a Bucket
    """    
    bucketname = bucketname.lower().strip()
    if minioClient.bucket_exists(bucketname):
        raise HTTPException(status_code=409, detail=f"Bucket {bucketname} already exists.")
    else:
        minioClient.make_bucket(bucketname)
        return {}


@router.get('/buckets/{bucketname}')
def listbucketitems(bucketname):
    """
    To List  Bucket Items
    """   
    bucket_items = [] 
    bucketname =  bucketname.lower().strip()
    if minioClient.bucket_exists(bucketname):
        objects = minioClient.list_objects(bucketname,recursive=True)
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
        
        abort(404)
        
@router.delete('/buckets/{bucketname}')
def removebucket(bucketname):
    """
    To remove a bucket
    """    
    bucketname =  bucketname.lower().strip()

    if minioClient.bucket_exists(bucketname):
        objects = list(minioClient.list_objects(bucketname))
        if objects:
          raise HTTPException(status_code=409, detail=f"Bucket {bucketname} not empty")
        else:
          minioClient.remove_bucket(bucketname)
          return {}
    else:
        raise HTTPException(status_code=404, detail=f"Bucket {bucketname} does not exist")

