import json
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
if not _key:
    raise RuntimeError(
        "CREDENTIAL_ENCRYPTION_KEY environment variable is not set. "
        "Set it to a Fernet key (generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")"
    )

fernet = Fernet(_key.encode())


def encrypt(username: str, password: str) -> str:
    authentication = {"username": username, "password": password}
    return fernet.encrypt(json.dumps(authentication).encode()).decode()


def decrypt(auth: str) -> dict:
    try:
        return json.loads(fernet.decrypt(auth.encode()))
    except InvalidToken as e:
        logger.error("Failed to decrypt credentials — token is invalid or the key has changed")
        raise ValueError("Credentials could not be decrypted") from e
    except Exception as e:
        logger.error("Unexpected error decrypting credentials: %s", e)
        raise
