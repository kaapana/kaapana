from __future__ import annotations

import io
import tarfile
import zipfile
from typing import Iterable, Iterator, Tuple

# See ``StorageBackend.fetch`` for the (arcname, size, chunks) contract.
FileStream = Iterable[Tuple[str, int, Iterator[bytes]]]

_BLOCK = tarfile.BLOCKSIZE  # 512


def stream_tar(files: FileStream) -> Iterator[bytes]:
    """Stream a tar archive of ``(arcname, size, chunks)`` members.

    Frames the tar manually so the response is drained *within* a member (not
    just between members): peak memory is ~one chunk regardless of member size.
    ``tarfile.TarInfo.tobuf`` produces the (PAX) header — PAX is pinned so long
    ``<entity-id>/<nested/s3/key>`` arcnames encode and re-read cleanly without
    appearing as extra ``getnames()`` entries.
    """
    for arcname, size, chunks in files:
        info = tarfile.TarInfo(name=arcname)
        info.size = size
        yield info.tobuf(tarfile.PAX_FORMAT)
        written = 0
        for chunk in chunks:
            written += len(chunk)
            yield chunk
        if written != size:
            # A wrong size silently misframes the next member — fail loudly.
            raise ValueError(f"{arcname}: declared size {size} but streamed {written} bytes")
        pad = (-size) % _BLOCK
        if pad:
            yield b"\x00" * pad
    # End-of-archive marker: two zero blocks, always emitted (a zero-member
    # request still produces a valid empty tar).
    yield b"\x00" * (_BLOCK * 2)


def stream_zip(files: FileStream) -> Iterator[bytes]:
    """Build a zip archive of ``(arcname, size, chunks)`` members.

    NOTE: buffered in memory for v1 (zip's central directory needs final
    offsets), so each member's chunks are joined here. Intended for the future
    UI download button; switch to a streaming zip writer if very large
    selections become common. ``size`` is unused (zip stores its own).
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, _size, chunks in files:
            zf.writestr(arcname, b"".join(chunks))
    yield buffer.getvalue()
