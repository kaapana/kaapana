import requests
from minio import Minio

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


def airflow_backend():
    r = requests.get('https://10.133.28.53/flow/kaapana/api/getdags', verify=False,  headers=get_auth_headers(
        'kaapana', 'admin', 'https', '10.133.28.53', '443', False, 'kaapana', '1c4645f0-e654-45a1-a8b6-cf28790104ea'
    ))
    print(r)
    print(r.json())

# def download_object_from_minio():
#     access_key='kaapanaminio'
#     secret_key='Kaapana2020'
#     minio_host='minio-service.store.svc'
#     minio_port='9000'
#     minioClient = Minio(minio_host+":"+minio_port,
#                         access_key=access_key,
#                         secret_key=secret_key,
#                         secure=False)

#     p_presigend_url = minioClient.get_presigned_url('PUT', 'january', 'aaa.txt')
#     r = requests.put(p_presigend_url, data=open('aaa.txt', 'rb'))
#     r
#     g_presigend_url = minioClient.get_presigned_url('GET', 'january', 'aaa.txt')
#     r = requests.get(g_presigend_url)
#     r.text