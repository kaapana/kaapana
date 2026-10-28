"""Shared fixtures: a fresh bucket on the test S3 server (NNUNET_TEST_S3=host:port) per test."""

import os
import uuid

import pytest
from kaapana_nnunet.store import S3Store
from minio import Minio

ENDPOINT = os.environ.get("NNUNET_TEST_S3")


@pytest.fixture
def client():
    return Minio(
        ENDPOINT,
        access_key=os.environ.get("NNUNET_TEST_S3_USER", "testadmin"),
        secret_key=os.environ.get("NNUNET_TEST_S3_PASSWORD", "testadmin123"),
        secure=False,
    )


@pytest.fixture
def store(client):
    bucket = f"test-{uuid.uuid4().hex[:12]}"
    client.make_bucket(bucket)
    yield S3Store(client, bucket)
    for obj in client.list_objects(bucket, recursive=True):
        client.remove_object(bucket, obj.object_name)
    client.remove_bucket(bucket)
