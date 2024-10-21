import asyncio
import requests
from fastapi import Request
from kaapanapy.helper import get_opensearch_client
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings
from opensearchpy.exceptions import RequestError

from .schemas import Project

logger = get_logger(__name__)


class OpenSearchHelper:
    """
    Helper class for managing project specific indices, roles and rolemappings in opensearch.
    """

    def __init__(self, access_token, wait_for_service=True):
        self.os_client = get_opensearch_client(access_token)
        self.access_token = access_token
        self.settings = OpensearchSettings()
        self.security_api_url = f"https://{self.settings.opensearch_host}:{self.settings.opensearch_port}/_plugins/_security/api"

        self.wait_for_service()

    def wait_for_service(self, max_retries=60, delay=5):
        """
        Wait until the opensearch service is reachable.
        """
        import time

        available = False
        tries = 0
        while not available:
            tries += 1
            try:
                r = requests.get(
                    f"https://{self.settings.opensearch_host}:{self.settings.opensearch_port}",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    verify=False,
                )
                r.raise_for_status()
                available = True
                logger.info("Opensearch available")
                return True
            except Exception as e:
                logger.warning(f"Opensearch not yet available: {str(e)}")
                time.sleep(delay)
                if tries >= max_retries:
                    logger.error(
                        f"Openseach not available after {max_retries} retries!"
                    )
                    raise e

    async def check_project_template_exists(
        self, template_name: str = "project_", max_retries=60, delay=5
    ):
        """
        Checks if the OpenSearch project template exists.
        """
        for tries in range(max_retries):
            # Check if the template exists
            template_url = f"https://{self.settings.opensearch_host}:{self.settings.opensearch_port}/_index_template/{template_name}"
            r = requests.get(
                template_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                },
                verify=False,
            )
            if r.status_code == 200:
                logger.info(f"Template '{template_name}' exists.")
                return
            elif r.status_code == 404:
                logger.info(
                    f"Template '{template_name}' does not exist yet, retrying..."
                )
            else:
                logger.warning(
                    f"Template '{template_name}' returned status {r.status_code}"
                )

            await asyncio.sleep(delay)

        logger.error(
            f"Opensearch template '{template_name}' not available after {max_retries} retries!"
        )
        raise Exception(f"Template '{template_name}' not found after retries")

    def create_index(self, index: str):
        """
        Create a new index in opensearch
        """
        self.os_client.indices.create(index)

    def create_role(self, role: str, index: str):
        """
        Create an opensearch role
        """
        payload = get_payload_for_role_and_index(role, index)
        role_name = conventional_role_name(role, index)
        logger.info(f"Create role {role_name}")
        response = requests.put(
            f"{self.security_api_url}/roles/{role_name}",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            verify=False,
        )
        response.raise_for_status()

    def create_rolemappings(self, role_name: str):
        """
        Create a role mapping in opensearch

        :role_name: Name of the opensearch role.
        """
        backend_role = role_name
        logger.info(f"Create rolemapping for {role_name}")
        payload = {
            "backend_roles": [backend_role]
        }  ### List of roles in the "opensearch" claim of the oidc access token
        response = requests.put(
            f"{self.security_api_url}/rolesmapping/{role_name}",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            verify=False,
        )
        response.raise_for_status()

    def setup_new_project(self, project: Project):
        """
        Create index, roles and rolemappings for a new project
        """
        index = f"project_{project.id}"
        try:
            self.create_index(index)
        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.warning("Resource already exists")
            else:
                raise e
        logger.info("Create opensearch roles and rolemappings")
        for role in ["admin", "read"]:
            self.create_role(role, index)
            role_name = conventional_role_name(role, index)
            self.create_rolemappings(role_name)


def get_opensearch_helper(request: Request) -> OpenSearchHelper:
    access_token = request.headers.get("x-forwarded-access-token")
    return OpenSearchHelper(access_token)


def get_payload_for_role_and_index(role, index):
    """
    Return the payload for creating a specific index role in opensearch,
    """
    allowed_actions = {
        "read": ["read"],
        "admin": [
            "data_access",
            "indices:admin/mappings/get",
        ],
    }
    cluster_permissions = {
        "read": ["cluster_composite_ops_ro"],
        "admin": ["cluster_composite_ops"],
    }
    assert role in allowed_actions.keys()
    return {
        "cluster_permissions": cluster_permissions.get(role),
        "index_permissions": [
            {
                "index_patterns": [index, ".opensearch_dashboards_1"],
                "dls": "",
                "fls": [],
                "masked_fields": [],
                "allowed_actions": allowed_actions.get(role),
            }
        ],
        "tenant_permissions": [],
    }


def conventional_role_name(role, index):
    """
    Convention for rolenames.
    Role names in opensearch should match claim values in the opensearch claim of the access token.
    """
    return f"{role}_{index}"
