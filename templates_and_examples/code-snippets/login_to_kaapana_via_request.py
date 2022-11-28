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
