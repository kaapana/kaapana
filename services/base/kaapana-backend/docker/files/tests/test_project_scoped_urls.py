"""
Regression tests for resolving the static website bucket from the Project header.

The Project header is optional on /get-static-website-results-html, so bucket
resolution must survive its absence: the previous inline code annotated
`bucket_name: str` but assigned the one-element TUPLE
`(DEFAULT_STATIC_WEBSITE_BUCKET,)`, and unconditionally called
`json.loads(request.headers.get("project"))`, which raises on a missing header.
No live services: fastapi/minio/opensearch are stubbed like in
test_admin_routers.py.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

# Stub heavy dependencies not installed in the test environment
for mod in (
    "app.config",
    "app.dependencies",
    "app.workflows.utils",
    "fastapi",
    "fastapi.responses",
    "jwt",
    "minio",
    "minio.error",
    "starlette",
    "starlette.responses",
    "opensearchpy",
    "requests",
):
    sys.modules.setdefault(mod, MagicMock())

import app.admin.routers as admin_routers  # noqa: E402


def test_static_website_bucket_without_project_header_is_default():
    # Unscoped requests exist (no cookie fallback anymore): must not crash and
    # must yield a usable bucket NAME (a str, not the historical tuple).
    bucket = admin_routers._resolve_static_website_bucket(None)
    assert bucket == admin_routers.DEFAULT_STATIC_WEBSITE_BUCKET
    assert isinstance(bucket, str)


def test_static_website_bucket_uses_project_bucket_from_header():
    raw = '{"short_id": "abc12345", "s3_bucket": "project-abc12345"}'
    assert admin_routers._resolve_static_website_bucket(raw) == "project-abc12345"


def test_static_website_bucket_falls_back_without_s3_bucket_field():
    assert (
        admin_routers._resolve_static_website_bucket('{"short_id": "abc12345"}')
        == admin_routers.DEFAULT_STATIC_WEBSITE_BUCKET
    )
