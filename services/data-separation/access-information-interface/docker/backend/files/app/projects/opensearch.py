import asyncio
import requests
from fastapi import Request
from kaapanapy.helper import get_opensearch_client
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings
from opensearchpy.exceptions import RequestError

from app.projects.schemas import Project
from app.projects.crud import get_rights

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

        if wait_for_service:
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

    def create_role(self, role_name: str, payload: dict):
        """
        Create an opensearch role

        :param claim_value: Name of the
        :param index: Name of the index the role should grant access to

        Return:
        Name of the role in opensearch.
        """
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
        return response

    def create_rolemappings(self, role_name: str, backend_role: str):
        """
        Create a role mapping in opensearch

        :role_name: Name of the opensearch role
        :backend_role: Name of the role in the access token.
        """
        logger.info(f"Create rolemapping for {role_name=} to {backend_role=}")
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

    async def setup_new_project(self, project: Project, session):
        """
        Create index, roles and rolemappings for a new project
        """
        index = project.opensearch_index
        try:
            self.os_client.indices.create(index)
        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.warning("Resource already exists")
            else:
                raise e
        logger.info("Create opensearch roles and rolemappings")

        db_rights = await get_rights(session)

        for right in db_rights:
            if not right.claim_key == "opensearch":
                continue
            claim_value = right.claim_value
            assert claim_value
            backend_role = f"{claim_value}_{project.id}"
            role_name = f"{claim_value}_{project.name}"

            payload = get_payload_for_claim_and_index(claim_value, index)
            self.create_role(role_name=role_name, payload=payload)
            self.create_rolemappings(role_name=role_name, backend_role=backend_role)

        return index


def get_opensearch_helper(request: Request) -> OpenSearchHelper:
    access_token = request.headers.get("x-forwarded-access-token")
    return OpenSearchHelper(access_token)


def get_payload_for_claim_and_index(claim_value: str, index):
    """
    Return the payload for creating a specific index role in opensearch

    :param claim_value:
    :param index:
    """
    allowed_actions = {
        "read_project": ["read"],
        "admin_project": [
            "data_access",
            "indices:admin/mappings/get",
        ],
    }
    cluster_permissions = {
        "read_project": ["cluster_composite_ops_ro"],
        "admin_project": ["cluster_composite_ops"],
    }
    assert claim_value in allowed_actions.keys()
    return {
        "cluster_permissions": cluster_permissions.get(claim_value),
        "index_permissions": [
            {
                "index_patterns": [index, ".opensearch_dashboards_1"],
                "dls": "",
                "fls": [],
                "masked_fields": [],
                "allowed_actions": allowed_actions.get(claim_value),
            }
        ],
        "tenant_permissions": [],
    }
