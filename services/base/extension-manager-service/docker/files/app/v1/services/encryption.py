import json
import os

from cryptography.fernet import Fernet

fernet = Fernet(os.environ["CREDENTIAL_ENCRYPTION_KEY"].encode())


def encrypt(username: str, password: str) -> str:
    authentication = {"username": username, "password": password}

    return fernet.encrypt(json.dumps(authentication).encode()).decode()


def decrypt(auth: str) -> dict:
    return json.loads(fernet.decrypt(auth.encode()))
