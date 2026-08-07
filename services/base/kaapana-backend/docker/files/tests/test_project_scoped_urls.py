"""
Regression tests for project-scoped resource URLs (thumbnails, result reports).

<img src> and iframe/document requests bypass the views' request interceptor,
so every URL the backend hands to a frontend must already carry the
/project/<short_id>/ prefix — otherwise the request arrives without a Project
header and the serving route fails. Guards the data-gallery-ui thumbnail 500 and
the results-browser report equivalent.
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
    "app.datasets.utils",
    "app.middlewares",
    "app.workflows.utils",
    "fastapi",
    "fastapi.responses",
    "jwt",
    "minio",
    "minio.error",
    "starlette",
    "starlette.responses",
    "starlette.types",
    "starlette.datastructures",
    "opensearchpy",
    "requests",
):
    sys.modules.setdefault(mod, MagicMock())

import app.admin.routers as admin_routers  # noqa: E402
import app.datasets.routers as datasets_routers  # noqa: E402

PROJECT = {"short_id": "abc12345", "s3_bucket": "project-abc12345"}


def test_thumbnail_url_is_project_scoped():
    url = datasets_routers._build_thumbnail_url(PROJECT, "1.2.3")
    assert url == "/project/abc12345/kaapana-backend/dataset/series/1.2.3/thumbnail"


def test_results_file_url_is_project_scoped():
    url = admin_routers._build_results_file_url(PROJECT, "batch/1.2.3/report.html")
    assert url == (
        "/project/abc12345/kaapana-backend/get-static-website-results-html"
        "?object_name=batch/1.2.3/report.html"
    )


def test_results_file_url_encodes_special_characters():
    url = admin_routers._build_results_file_url(PROJECT, "batch/a b&c/report.html")
    assert url == (
        "/project/abc12345/kaapana-backend/get-static-website-results-html"
        "?object_name=batch/a%20b%26c/report.html"
    )


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
