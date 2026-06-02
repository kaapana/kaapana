from __future__ import annotations

from typing import Iterator, Optional, Tuple


class StorageBackend:
    """Move raw bytes from a single store, store-agnostically."""

    store_type: str = ""

    def fetch(
        self, coordinate, access_token: Optional[str]
    ) -> Iterator[Tuple[str, bytes]]:
        """Yield ``(relative_path, content)`` for the data at ``coordinate``.

        A PACS series yields one entry per instance; an S3 object yields one.
        """
        raise NotImplementedError
