"""A project role keeps access to the Dashboards saved objects after Dashboards has
migrated them to a new .opensearch_dashboards_<n> index (kaapana#2502)."""

import os
import sys
from fnmatch import fnmatch
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))
# kaapanapy and opensearch-py are not installed in the test environment, and
# app.database needs a database driver.
for name in (
    "kaapanapy",
    "kaapanapy.helper",
    "kaapanapy.logger",
    "kaapanapy.settings",
    "opensearchpy",
    "opensearchpy.exceptions",
    "app.database",
):
    sys.modules.setdefault(name, MagicMock())
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused")
os.environ.setdefault("PLATFORM_PREFIX", "kaapana")

from app.projects.opensearch import get_payload_for_claim_and_index  # noqa: E402


@pytest.mark.parametrize("claim_value", ["read_project", "admin_project"])
@pytest.mark.parametrize(
    "dashboards_index", [".opensearch_dashboards_1", ".opensearch_dashboards_2"]
)
def test_project_role_reaches_every_migrated_dashboards_index(
    claim_value, dashboards_index
):
    payload = get_payload_for_claim_and_index(claim_value, "project_study")
    patterns = payload["index_permissions"][0]["index_patterns"]
    assert any(fnmatch(dashboards_index, pattern) for pattern in patterns)
    assert "project_study" in patterns
