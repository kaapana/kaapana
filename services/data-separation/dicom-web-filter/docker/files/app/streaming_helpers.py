import httpx
from fastapi import Request


async def metadata_replace_stream(
    method: str = "GET",
    url: str = None,
    request: Request = None,
    search: bytes = None,
    replace: bytes = None,
):
    """Replace a part of the response stream with another part. Used to replace the boundary used in multipart responses.

    Args:
        method (str, optional): Method to use for the request. Defaults to "GET".
        url (str, optional): URL to send the request to. Defaults to None.
        request (Request, optional): Request object. Defaults to None.
        search (bytes, optional): Part of the response to search for (which will be replaced). Defaults to None.
        replace (bytes, optional): Bytes to replace the search with. Defaults to None.

    Yields:
        bytes: Part of the response stream
    """
    buffer = b""
    pattern_size = len(search)
    async with httpx.AsyncClient() as client:
        async with client.stream(
            method,
            url,
            params=dict(request.query_params),
            headers=dict(request.headers),
        ) as response:
            async for chunk in response.aiter_bytes():
                buffer += chunk
                # Process the buffer
                buffer = buffer.replace(search, replace)
                to_yield = buffer[:-pattern_size] if len(buffer) > pattern_size else b""
                yield to_yield
                buffer = buffer[-pattern_size:]  # Retain this much of the buffer

            # Yield any remaining buffer after the last chunk
            if buffer:
                yield buffer
