"""Async client for the Kaapana Data API.

Covers the read/query and write operations Python callers use today: query +
entity lookup + dataset resolution, plus entity creation, metadata-schema
registration, metadata attachment and artifact upload. It contains NO
store-access logic — fetching the underlying bytes is the Storage API's job (see
``StorageClient``). The Data API has no auth today; an access token is attached
when provided so this is ready for when it does.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from data_api._http import (
    auth_headers,
    default_data_api_url,
    request_with_retries,
)

logger = logging.getLogger(__name__)

CONTAINS_LINK_TYPE = "contains"


class DataClient:
    """Async HTTP client for the Data API.

    Use as an async context manager so the underlying ``httpx.AsyncClient`` is
    closed::

        async with DataClient(access_token=token) as data:
            ids = await data.query_index(where={...})
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: int = 30,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.base_url = (base_url or default_data_api_url()).rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers=auth_headers(access_token),
            transport=transport,
        )

    async def __aenter__(self) -> "DataClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------ read
    async def query(
        self,
        where: Optional[dict] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """Run a paged query, returning the raw QueryResponse dict."""
        payload: Dict[str, Any] = {"where": where, "limit": limit}
        if cursor:
            payload["cursor"] = cursor
        response = await request_with_retries(
            self._client, "POST", f"{self.base_url}/entities/query", json=payload
        )
        response.raise_for_status()
        return response.json()

    async def query_index(self, where: Optional[dict] = None) -> List[str]:
        """Resolve a query to the full ordered list of matching entity IDs.

        This is the freeze primitive: ``/entities/query/index`` streams a single
        JSON object containing every matching ID (paginated via ``next_cursor``).
        """
        ids: List[str] = []
        cursor: Optional[str] = None
        while True:
            payload: Dict[str, Any] = {"where": where}
            if cursor:
                payload["cursor"] = cursor
            response = await request_with_retries(
                self._client,
                "POST",
                f"{self.base_url}/entities/query/index",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            ids.extend(data.get("items", []))
            cursor = data.get("next_cursor")
            if not cursor:
                break
        return ids

    async def get_entity(self, entity_id: str) -> dict:
        """Fetch a full entity record (storage_coordinates, metadata, links)."""
        response = await request_with_retries(
            self._client, "GET", f"{self.base_url}/entities/{entity_id}"
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_storage_coordinates(entity: dict) -> List[dict]:
        """Return the storage coordinates of an entity record."""
        return entity.get("storage_coordinates", [])

    async def resolve_dataset_members(
        self, dataset_entity_id: str, extra_where: Optional[dict] = None
    ) -> List[str]:
        """Resolve a dataset entity to its member IDs via ``contains`` links.

        Uses ``descendant_of`` so it composes (optionally ANDed with
        ``extra_where``) into a single index query. NOTE: ``descendant_of`` is
        recursive, so members of nested sub-datasets are included.
        """
        member_filter = {
            "type": "filter",
            "op": "descendant_of",
            "value": {
                "entity_id": dataset_entity_id,
                "link_type": CONTAINS_LINK_TYPE,
            },
        }
        if extra_where is None:
            where: dict = member_filter
        else:
            where = {
                "type": "group",
                "op": "and",
                "children": [member_filter, extra_where],
            }
        return await self.query_index(where)

    # ----------------------------------------------------------------- write
    async def register_metadata_schema(self, key: str, schema: dict) -> dict:
        """Register (or replace) the JSON schema for a metadata key.

        ``POST /metadata/keys/{key}`` is register-or-replace, so this is idempotent.
        """
        response = await request_with_retries(
            self._client, "POST", f"{self.base_url}/metadata/keys/{key}", json=schema
        )
        response.raise_for_status()
        return response.json()

    async def create_entity(self, entity: dict) -> dict:
        """Create or replace an entity (id, storage_coordinates, metadata)."""
        response = await request_with_retries(
            self._client, "POST", f"{self.base_url}/entities", json=entity
        )
        response.raise_for_status()
        return response.json()

    async def attach_metadata(
        self,
        entity_id: str,
        key: str,
        data: dict,
        artifacts: Optional[list] = None,
    ) -> dict:
        """Attach (or replace) a metadata entry on an entity.

        The key's schema must be registered first or the Data API returns 4xx.
        """
        payload = {"key": key, "data": data, "artifacts": artifacts or []}
        response = await request_with_retries(
            self._client,
            "POST",
            f"{self.base_url}/entities/{entity_id}/metadata",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def upload_artifact(
        self,
        entity_id: str,
        key: str,
        artifact_id: str,
        content: Any,
        *,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> dict:
        """Upload a binary artifact for a metadata entry (multipart ``file=``).

        Not retried: the multipart body would be consumed on the first attempt.
        ``content`` may be bytes or a binary file object.
        """
        files = {
            "file": (
                filename or artifact_id,
                content,
                content_type or "application/octet-stream",
            )
        }
        response = await self._client.post(
            f"{self.base_url}/entities/{entity_id}/metadata/{key}/artifacts/{artifact_id}",
            files=files,
        )
        response.raise_for_status()
        return response.json()
