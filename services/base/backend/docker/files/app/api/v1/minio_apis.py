
from flask import jsonify, abort

from . import api_v1

from minio import Minio
import os
import requests
import json
from datetime import datetime
import socket



#Production
_minio_host='minio-service.store.svc'

#Local Testing
#_minio_host='127.0.0.1'

_minio_port='9000'

#Initializing Minio Client
minioClient = Minio(_minio_host+":"+_minio_port,
                            access_key="kaapanaminio",
                        secret_key="Kaapana2020",
                        
                        secure=False)


@api_v1.route('/minio/listbuckets/')
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
        #link = hyperlink.parse(f'{socket.gethostname()}/minio/{str(bucket.name)}')
        data.append({'bucket_name':str(bucket.name),'creation_date':millisec,'link':f'{socket.gethostname()}/minio/{str(bucket.name)}'})
        
        
        
    return json.dumps(data)

@api_v1.route('/minio/makebucket/<string:bucketname>/', methods=['GET'])
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

@api_v1.route('/minio/listbucketitems/<string:bucketname>/', methods=['GET'])
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
        #return f"{bucketname} is not available"

@api_v1.route('/minio/removebucket/<string:bucketname>/', methods=['GET'])
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

