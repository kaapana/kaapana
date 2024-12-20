from kaapanapy.helper import get_project_user_access_token
from kaapanapy.settings import OpensearchSettings
from kaapanapy.logger import get_logger
import requests
import os
from time import sleep

logger = get_logger(__name__)
opensearch_settings = OpensearchSettings()
username = "kaapanaopensearch"


def create_dashboard_user_in_opensearch_backend():
    access_token = get_project_user_access_token()
    response = requests.put(
        f"https://{opensearch_settings.opensearch_host}:{opensearch_settings.opensearch_port}/_plugins/_security/api/internalusers/{username}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "password": os.getenv("KAAPANA_KIBANASERVER_PASSWORD"),
            "opendistro_security_roles": [],
            "backend_roles": ["admin"],
            "attributes": {},
        },
        verify=False,
    )
    logger.debug(f"{response.text}")
    response.raise_for_status()


if __name__ == "__main__":
    success = False
    for _ in range(10):
        try:
            create_dashboard_user_in_opensearch_backend()
            logger.info(f"Successfully created user {username} in opensearch backend.")
            success = True
            break
        except Exception as e:
            logger.warning(str(e))
            logger.warning("Retry ...")
            sleep(12)
            error = e

    if not success:
        logger.error(f"fFailed to create user {username}")
        raise error
