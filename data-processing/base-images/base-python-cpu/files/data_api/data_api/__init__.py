"""Async client SDK for the Kaapana Data API and Storage API.

This package is the single programmatic gate to the Data API for Python callers
(operators, processing containers, backend services). Import the clients from the
top level:

    from data_api import DataClient, StorageClient
"""

from data_api.data.client import CONTAINS_LINK_TYPE, DataClient
from data_api.storage.client import StorageClient

__all__ = ["DataClient", "StorageClient", "CONTAINS_LINK_TYPE"]
