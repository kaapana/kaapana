"""Shared HTTP helpers for the Data API clients.

Keeps the clients kaapanapy-free: default service URLs are derived from plain
environment variables, and retry/backoff is implemented here (urllib3's ``Retry``
is requests-only and has no httpx equivalent).
"""

import asyncio
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Status codes worth retrying (rate limiting + transient server errors).
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


def services_namespace() -> str:
    """Resolve the in-cluster services namespace from the environment."""
    return (
        os.environ.get("KAAPANA_SERVICES_NAMESPACE")
        or os.environ.get("SERVICES_NAMESPACE")
        or "services"
    )


def default_data_api_url() -> str:
    """Default Data API base URL (in-cluster service DNS, no ingress prefix)."""
    explicit = os.environ.get("KAAPANA_DATA_API_URL")
    if explicit:
        return explicit
    return f"http://data-api.{services_namespace()}.svc/v1"


def default_storage_api_url() -> str:
    """Default Storage API base URL (service root; ``/v1/...`` appended by callers)."""
    explicit = os.environ.get("KAAPANA_STORAGE_API_URL")
    if explicit:
        return explicit
    return f"http://storage-api.{services_namespace()}.svc"


def auth_headers(access_token: Optional[str]) -> dict:
    """Build auth headers. The Data API has no auth today; this is forward-ready."""
    if not access_token:
        return {}
    return {
        "Authorization": f"Bearer {access_token}",
        "x-forwarded-access-token": access_token,
    }


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    retries: int = 3,
    backoff_factor: float = 1.0,
    **kwargs,
) -> httpx.Response:
    """Issue a request, retrying on 429/5xx with exponential backoff.

    Only safe for idempotent/replayable payloads (JSON bodies) — do NOT use for
    streamed file uploads, whose body would be consumed on the first attempt.
    """
    response: Optional[httpx.Response] = None
    for attempt in range(retries + 1):
        response = await client.request(method, url, **kwargs)
        if response.status_code in _RETRY_STATUS and attempt < retries:
            delay = backoff_factor * (2**attempt)
            logger.warning(
                "Data API %s %s -> %s; retry %d/%d in %.1fs",
                method,
                url,
                response.status_code,
                attempt + 1,
                retries,
                delay,
            )
            await asyncio.sleep(delay)
            continue
        return response
    return response  # pragma: no cover - loop always returns
