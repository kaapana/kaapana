from __future__ import annotations

import io
import tarfile
import zipfile
from typing import Iterable, Iterator, Tuple

FileStream = Iterable[Tuple[str, bytes]]


class _StreamBuffer:
    """A minimal write-only file object that collects bytes for draining.

    Lets ``tarfile`` in streaming mode (``w|``) write into a generator without
    seeking, so the archive is produced incrementally and only one member's
    bytes are held in memory at a time.
    """

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, data: bytes) -> int:
        self._chunks.append(data)
        return len(data)

    def drain(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


def stream_tar(files: FileStream) -> Iterator[bytes]:
    """Stream a tar archive of ``(arcname, content)`` pairs."""
    buffer = _StreamBuffer()
    tar = tarfile.open(fileobj=buffer, mode="w|")
    try:
        for arcname, content in files:
            info = tarfile.TarInfo(name=arcname)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
            chunk = buffer.drain()
            if chunk:
                yield chunk
    finally:
        tar.close()
    chunk = buffer.drain()
    if chunk:
        yield chunk


def stream_zip(files: FileStream) -> Iterator[bytes]:
    """Build a zip archive of ``(arcname, content)`` pairs.

    NOTE: buffered in memory for v1 (zip's central directory needs final
    offsets). Intended for the future UI download button; switch to a streaming
    zip writer if very large selections become common.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, content in files:
            zf.writestr(arcname, content)
    yield buffer.getvalue()
