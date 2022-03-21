import requests
from datetime import timedelta


from minio import Minio

def get_presigend_url(minioClient, method, bucket_name, object_name, expires=timedelta(days=7)):
    presigend_url = minioClient.get_presigned_url(method, bucket_name, object_name, expires=expires)
    return {'method': method, 'path': presigend_url.replace(f'{minioClient._base_url._url.scheme}://{minioClient._base_url._url.netloc}', '')}

def get_minio_client(access_key, secret_key, minio_host='minio-service.store.svc', minio_port='9000'):
    minioClient = Minio(minio_host+":"+minio_port,
                        access_key=access_key,
                        secret_key=secret_key,
                        secure=False)
    return minioClient

def get_remote_header(token):
    return {'FederatedAuthorization': f'{token}'}

def get_auth_headers(username, password, protocol, host, port, ssl_check, client_id, client_secret):
    payload = {
        'username': username,
        'password': password,
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'password'
    }
    url = f'{protocol}://{host}:{port}/auth/realms/kaapana/protocol/openid-connect/token'
    r = requests.post(url, verify=ssl_check, data=payload)
    access_token = r.json()['access_token']
    return {'Authorization': f'Bearer {access_token}'}