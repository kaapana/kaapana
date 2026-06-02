"""Async client for the Kaapana Storage API.

Materialises entity bytes onto disk without knowing PACS from S3: it sends the
Data API storage coordinates to the storage-api, which streams back a tar
archive. The archive is unpacked into the output directory as
``<entity_id>/<files>``.
"""

import asyncio
import logging
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional

import httpx

from data_api._http import auth_headers, default_storage_api_url

logger = logging.getLogger(__name__)


def _extract_tar(archive_path: Path, output: Path) -> None:
    """Extract a tar archive into ``output`` (py3.12+ safe ``filter='data'``)."""
    with tarfile.open(name=str(archive_path), mode="r") as tar:
        try:
            tar.extractall(path=output, filter="data")
        except TypeError:  # filter kwarg unavailable < py3.12
            tar.extractall(path=output)


class StorageClient:
    """Async HTTP client for the Storage API.

    Use as an async context manager::

        async with DataClient(access_token=t) as data, \\
                   StorageClient(access_token=t) as storage:
            await storage.download_entities(ids, "/out", data_client=data)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: int = 3600,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.base_url = (base_url or default_storage_api_url()).rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers=auth_headers(access_token),
            transport=transport,
        )

    async def __aenter__(self) -> "StorageClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def download(
        self, items: List[dict], output_dir, format: str = "tar"
    ) -> Path:
        """Stream the storage-api archive for ``items`` and unpack into ``output_dir``.

        ``tarfile`` is synchronous and cannot read an async byte stream, so the
        response is streamed to a temp file first, then extracted off the event
        loop via ``asyncio.to_thread``.
        """
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        url = f"{self.base_url}/v1/download"
        logger.info("Requesting %d items from storage-api at %s", len(items), url)

        tmp = tempfile.NamedTemporaryFile(suffix=".tar", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        try:
            async with self._client.stream(
                "POST", url, json={"items": items, "format": format}
            ) as response:
                response.raise_for_status()
                with open(tmp_path, "wb") as fh:
                    async for chunk in response.aiter_bytes():
                        fh.write(chunk)
            await asyncio.to_thread(_extract_tar, tmp_path, output)
        finally:
            tmp_path.unlink(missing_ok=True)
        return output
