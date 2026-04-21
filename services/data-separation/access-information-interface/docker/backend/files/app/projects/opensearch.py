import asyncio
import re

import httpx
import requests
from app.projects.crud import get_rights
from app.projects.schemas import Project
from kaapanapy.helper import get_opensearch_client, get_project_user_access_token
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings
from opensearchpy.exceptions import RequestError

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

    async def create_role(self, role_name: str, payload: dict):
        """
        Create an opensearch role

        :param role_name: Name of the opensearch role
        :param payload: Role definition payload

        Return:
        Name of the role in opensearch.
        """
        logger.info(f"Create role {role_name}")

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.put(
                f"{self.security_api_url}/roles/{role_name}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()
        return response

    async def create_rolemappings(self, role_name: str, backend_role: str):
        """
        Create a role mapping in opensearch

        :role_name: Name of the opensearch role
        :backend_role: Name of the role in the access token.
        """
        logger.info(f"Create rolemapping for {role_name=} to {backend_role=}")
        payload = {
            "backend_roles": [backend_role]
        }  ### List of roles in the "opensearch" claim of the oidc access token
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.put(
                f"{self.security_api_url}/rolesmapping/{role_name}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()

    def _alias_name(self, project_name: str) -> str:
        """
        Return the human-readable OpenSearch alias for the given project name.
        """
        return f"project-{project_name.lower()}"

    async def _set_alias(self, index: str, alias: str):
        """
        Create (or replace) the alias alias pointing to index.
        """
        url = (
            f"https://{self.settings.opensearch_host}:{self.settings.opensearch_port}"
            f"/{index}/_alias/{alias}"
        )
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.put(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        if response.status_code not in (200, 201, 204):
            logger.warning(
                f"Failed to create alias {alias} -> {index}: {response.text}"
            )
        else:
            logger.info(f"Alias: {alias} -> Index: {index}")

    async def _remove_alias(self, index: str, alias: str):
        """
        Remove the alias alias from index if it exists.
        """
        url = (
            f"https://{self.settings.opensearch_host}:{self.settings.opensearch_port}"
            f"/{index}/_alias/{alias}"
        )
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        if response.status_code == 404:
            logger.info(f"Alias {alias!r} did not exist, skipping removal.")
        elif response.status_code not in (200, 201):
            logger.warning(f"Failed to remove alias {alias!r}: {response.text}")
        else:
            logger.info(f"Alias {alias!r} removed.")

    async def setup_new_project(self, project: Project, session):
        """
        Create index, alias, roles and rolemappings for a new project
        """
        logger.info(f"opensearch index setting for {project.__dict__}")
        index = project.opensearch_index
        alias = self._alias_name(project.name)

        # Create the physical index
        try:
            self.os_client.indices.create(index)
            logger.info(f"Created OpenSearch index {index!r}")
        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.warning(f"Index {index!r} already exists")
            else:
                raise e
        await self._set_alias(index, alias)

        logger.info("Create opensearch roles and rolemappings")

        db_rights = await get_rights(session)

        for right in db_rights:
            if not right.claim_key == "opensearch":
                continue
            claim_value = right.claim_value
            assert claim_value
            # backend_role and role_name are UUID-based → stable across renames
            backend_role = f"{claim_value}_{project.id}"
            role_name = f"{claim_value}_{project.id}"

            # give access to both the real index and the alias
            payload = get_payload_for_claim_and_index(claim_value, index)
            await self.create_role(role_name=role_name, payload=payload)
            await self.create_rolemappings(
                role_name=role_name, backend_role=backend_role
            )

        return index

    async def update_project_alias(self, project: Project, old_name: str):
        """
        Rename the human-readable alias when a project is renamed.

        Removes the old alias and creates a new one pointing to the same index

        :param project: Updated project object (project.name is the *new* name)
        :param old_name: Previous project name
        """
        index = project.opensearch_index
        old_alias = self._alias_name(old_name)
        new_alias = self._alias_name(project.name)

        if old_alias == new_alias:
            return  # Name unchanged

        await self._remove_alias(index, old_alias)
        await self._set_alias(index, new_alias)
        logger.info(
            f"Renamed OpenSearch alias from {old_alias!r} to {new_alias!r} "
            f"(index {index!r} unchanged)"
        )

    async def teardown_project(
        self, project: Project, session, retain_data: bool = False
    ):
        """
        Remove roles and rolemappings for the project.
        Removes the alias and, unless retain_data is True, the physical index.
        """
        db_rights = await get_rights(session)

        for right in db_rights:
            if not right.claim_key == "opensearch":
                continue
            claim_value = right.claim_value
            role_name = f"{claim_value}_{project.id}"
            logger.info(f"Deleting opensearch rolemapping and role for {role_name=}")

            async with httpx.AsyncClient(verify=False) as client:
                # delete rolemapping first
                try:
                    response = await client.delete(
                        f"{self.security_api_url}/rolesmapping/{role_name}",
                        headers={"Authorization": f"Bearer {self.access_token}"},
                    )
                    response.raise_for_status()
                except Exception as e:
                    logger.warning(f"Failed to delete rolemapping {role_name}: {e}")

                # then delete the role
                try:
                    response = await client.delete(
                        f"{self.security_api_url}/roles/{role_name}",
                        headers={"Authorization": f"Bearer {self.access_token}"},
                    )
                    response.raise_for_status()
                except Exception as e:
                    logger.warning(f"Failed to delete role {role_name}: {e}")

        # Always remove the human-readable alias
        alias = self._alias_name(project.name)
        await self._remove_alias(project.opensearch_index, alias)

        if not retain_data:
            index = project.opensearch_index
            logger.info(f"Deleting opensearch index {index}")
            try:
                self.os_client.indices.delete(index)
            except Exception as e:
                logger.warning(f"Failed to delete index {index}: {e}")


def get_opensearch_helper() -> OpenSearchHelper:
    access_token = get_project_user_access_token()
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


def is_valid_opensearch_index_name(index_name: str) -> bool:
    r"""
    https://opensearch.org/docs/1.1/opensearch/rest-api/index-apis/create-index/
    Index naming restrictions
    OpenSearch indices have the following naming restrictions:

    All letters must be lowercase.
    Index names can't begin with underscores (_) or hyphens (-).
    Index names can't contain spaces, commas, or the following characters:
        :, ", *, +, /, \\, |, ?, #, >, or <
    """
    # Check for lowercase, length, and valid characters based on OpenSearch restrictions
    if not (1 <= len(index_name) <= 255):
        return False
    # Validate characters and starting rules
    if not re.fullmatch(r"^[a-z0-9][a-z0-9\-\_]*$", index_name):
        return False
    # Ensure it does not contain any prohibited characters
    if any(c in index_name for c in ' :,"*+/\\|?#><'):
        return False
    return True
