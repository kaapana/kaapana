
from flask import jsonify, abort

from . import api_v1

from minio import Minio
import os
import requests
import json
from datetime import datetime
import socket

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


@api_v1.route('/minio/buckets/')
def listbuckets():
    """Return List of Minio buckets
    To List Buckets
    ---
    tags:
      - Minio APIs
   
    responses:
      200:
        description: Return List of Minio buckets
    """
    buckets = minioClient.list_buckets()
    data = []
   

    for bucket in buckets:
      
        millisec = (bucket.creation_date).timestamp() * 1000
        
        data.append({'bucket_name':str(bucket.name),'creation_date':millisec,'link':f'{socket.gethostname()}/minio/{str(bucket.name)}'})
        
        
        
    return json.dumps(data)

@api_v1.route('/minio/bucket/<string:bucketname>/', methods=['POST'])
def makebucket(bucketname):
    """
    To Create a Bucket
    ---
    tags:
      - Minio APIs
    parameters:
      - name: bucketname
        in: path
        type: string
        required: true
        description: Enter bucket name
    responses:
      200:
        description: Success
    """    
    print('"""""""""""""""""""""""',bucketname)
    bucketname =  bucketname.lower().strip()
    if minioClient.bucket_exists(bucketname):
        return f"{bucketname} Already Exist."
    else:
        minioClient.make_bucket(bucketname)
        return f"{bucketname} created successfully"

@api_v1.route('/minio/bucketitemslist/<string:bucketname>/', methods=['GET'])
def listbucketitems(bucketname):
    """
    To List  Bucket Items
    ---
    tags:
      - Minio APIs
    parameters:
      - name: bucketname
        in: path
        type: string
        required: true
        description: Enter bucket name
    responses:
      200:
        description: Success
      404:
        description: If the bucket does not
    """   
    bucket_items = [] 
    bucketname =  bucketname.lower().strip()
    if minioClient.bucket_exists(bucketname):
        objects = minioClient.list_objects(bucketname,recursive=True)
        for obj in objects:
          
          bucket_items.append({'bucket_name':str(obj.bucket_name), \
                                'object_name':str(obj.object_name), \
                                'last_modified':(obj.last_modified).timestamp() * 1000, \
                                'etag':obj.etag, \
                                'size':obj.size, \
                                'type':obj.content_type})      

        return json.dumps(bucket_items)
    else:
        
        abort(404)
        

@api_v1.route('/minio/bucketremove/<string:bucketname>/', methods=['POST'])
def removebucket(bucketname):
    """
    To remove a bucket
    
    ---
    tags:
      - Minio APIs
    parameters:
      - name: bucketname
        in: path
        type: string
        required: true
        description: Enter bucket name to remove
    responses:
      200:
        description: Success
      404:
        description: If the bucket does not exist
    """    
    bucketname =  bucketname.lower().strip()
    if minioClient.bucket_exists(bucketname):
        minioClient.remove_bucket(bucketname)
        return f"{bucketname} Removed Successfully"
    else:
        abort(404)
        #return f"{bucketname} Does not exist"

