"""Async client for the Kaapana Storage API.

Materialises entity bytes onto disk without knowing PACS from S3: it sends the
Data API storage coordinates to the storage-api, which streams back a tar
archive. The archive is unpacked into the output directory as
``<entity_id>/<files>``.
"""

import asyncio
import json
import logging
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional

import httpx

from data_api._http import _RETRY_STATUS, auth_headers, default_storage_api_url

logger = logging.getLogger(__name__)


def _extract_tar(archive_path: Path, output: Path) -> None:
    """Extract a tar archive into ``output`` (py3.12+ safe ``filter='data'``)."""
    with tarfile.open(name=str(archive_path), mode="r") as tar:
        try:
            tar.extractall(path=output, filter="data")
        except TypeError:  # filter kwarg unavailable < py3.12
            tar.extractall(path=output)


def _verify_complete(entity_ids: List[str], output: Path) -> None:
    """Assert every requested entity produced a non-empty directory."""
    missing = [
        entity_id
        for entity_id in entity_ids
        if not (output / entity_id).is_dir() or not any((output / entity_id).iterdir())
    ]
    if missing:
        raise RuntimeError(
            f"Incomplete download: {len(missing)}/{len(entity_ids)} entities produced "
            f"no files (truncated stream or empty storage?): {missing}"
        )


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
        connect_timeout: float = 10.0,
        read_timeout: float = 120.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        # storage-api root; "/v1/download" is appended by the methods.
        self.base_url = (base_url or default_storage_api_url()).rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        # ``timeout`` bounds writes and pool waits only. The read timeout is per
        # chunk, so it caps the silence between bytes, not the transfer: a peer
        # that vanished without a TCP reset (a force-deleted pod) is detected in
        # ``read_timeout`` seconds and retried instead of hanging for an hour.
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=connect_timeout, read=read_timeout),
            headers=auth_headers(access_token),
            transport=transport,
        )

    async def __aenter__(self) -> "StorageClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def download(self, items: List[dict], output_dir, format: str = "tar") -> Path:
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
            async with self._client.stream("POST", url, json={"items": items, "format": format}) as response:
                response.raise_for_status()
                with open(tmp_path, "wb") as fh:
                    async for chunk in response.aiter_bytes():
                        fh.write(chunk)
            await asyncio.to_thread(_extract_tar, tmp_path, output)
        finally:
            tmp_path.unlink(missing_ok=True)
        return output

    async def upload(
        self,
        files: List[tuple],
        store: str,
        target: dict,
    ) -> List[dict]:
        """Write ``files`` to ``store`` via the storage-api; return coordinates.

        The mirror image of :meth:`download`: the storage-api moves bytes only,
        and returns the storage coordinates the caller records on a new Data API
        entity. ``files`` is a list of ``(filename, content)`` pairs (content is
        bytes or a binary file object); ``target`` carries the store-specific
        routing (s3: ``bucket``/``key_prefix`` and optional ``unit`` —
        ``"folder"`` returns one prefix coordinate, ``"file"`` one object
        coordinate; pacs: optional ``pacs_id``).

        Not retried: the multipart body would be consumed on the first attempt
        (mirrors ``DataClient.upload_artifact``).
        """
        descriptor = {"store": store, **target}
        multipart = [("files", (filename, content, "application/octet-stream")) for filename, content in files]
        response = await self._client.post(
            f"{self.base_url}/v1/upload",
            data={"descriptor": json.dumps(descriptor)},
            files=multipart,
        )
        response.raise_for_status()
        return response.json()["coordinates"]

    async def download_entities(
        self,
        entity_ids: List[str],
        output_dir,
        data_client,
        format: str = "tar",
        max_concurrency: int = 10,
        download_retries: int = 3,
        retry_backoff: float = 1.0,
    ) -> Path:
        """Resolve each entity's coordinates via ``data_client`` and download them.

        ``data_client`` is a ``DataClient`` (or compatible: awaitable
        ``get_entity`` + ``get_storage_coordinates``).

        Entities are resolved and downloaded concurrently, up to
        ``max_concurrency`` at a time (one ``/v1/download`` request per entity,
        each unpacked into ``<entity_id>/``). This bounds simultaneous
        connections to the storage-api and gives per-entity failure isolation
        (an earlier single-request design bundled every entity into one tar).

        Each per-entity download is retried up to ``download_retries`` times with
        exponential backoff (``retry_backoff * 2**attempt`` seconds) on transient
        failures — transport errors (incl. a storage-api dropping the connection
        mid-stream when it restarts) and retryable 5xx/429. The ``/v1/download``
        request body is small replayable JSON, so re-issuing it is safe (unlike a
        streamed upload). Non-retryable errors (4xx, a corrupt archive) fail fast.
        A failed attempt never touches ``<entity_id>/``: :meth:`download` stages
        the archive in a temp file and unpacks it only once fully received.
        """
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        if not entity_ids:
            logger.warning("No entity IDs provided; nothing to download.")
            return output

        semaphore = asyncio.Semaphore(max(1, max_concurrency))
        retries = max(0, download_retries)

        async def _one(entity_id: str) -> None:
            async with semaphore:
                entity = await data_client.get_entity(entity_id)
                item = {
                    "id": entity_id,
                    "coordinates": data_client.get_storage_coordinates(entity),
                }
                last_exc: Optional[Exception] = None
                for attempt in range(retries + 1):
                    try:
                        await self.download([item], output, format=format)
                        return
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code not in _RETRY_STATUS:
                            raise
                        last_exc = exc
                    except httpx.TransportError as exc:
                        last_exc = exc
                    if attempt < retries:
                        delay = retry_backoff * (2**attempt)
                        logger.warning(
                            "entity %s download failed (%s); retry %d/%d in %.1fs",
                            entity_id,
                            type(last_exc).__name__,
                            attempt + 1,
                            retries,
                            delay,
                        )
                        await asyncio.sleep(delay)
                raise last_exc

        await asyncio.gather(*(_one(eid) for eid in entity_ids))
        await asyncio.to_thread(_verify_complete, entity_ids, output)
        logger.info(
            "Downloaded %d entities into %s (max_concurrency=%d)",
            len(entity_ids),
            output,
            max_concurrency,
        )
        return output
