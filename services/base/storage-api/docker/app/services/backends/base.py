from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Tuple


class StorageBackend:
    """Move raw bytes to/from a single store, store-agnostically.

    Implementations are stateless singletons; the per-request access token is
    passed into :meth:`fetch`/:meth:`store` so the service holds no credentials
    of its own.
    """

    store_type: str = ""

    def fetch(
        self, coordinate, access_token: Optional[str]
    ) -> Iterator[Tuple[str, bytes]]:
        """Yield ``(relative_path, content)`` for the data at ``coordinate``.

        A PACS series yields one entry per instance; an S3 object yields one.
        """
        raise NotImplementedError

    def store(
        self,
        target,
        files: Iterable[Tuple[str, bytes]],
        access_token: Optional[str],
    ) -> List:
        """Write ``(filename, content)`` files to ``target`` and return the
        concrete storage coordinates the bytes are now addressable by.
        """
        raise NotImplementedError
