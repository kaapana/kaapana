"""
Unit test for kaapana-backend dataset field mapping.

Guards that get_field_mapping works when the project index is an alias:
OpenSearch keys the get_mapping reply by the real index name, not the alias.
The OpenSearch client is a MagicMock — no live cluster needed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make the app package importable and stub kaapanapy (not installed here).
FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))
sys.modules.setdefault("kaapanapy", MagicMock())
sys.modules.setdefault("kaapanapy.settings", MagicMock())

import app.datasets.utils as utils  # noqa: E402


def test_get_field_mapping_resolves_alias_to_real_index():
    os_client = MagicMock()
    # alias project_a0841558 points at the migrated index project_testp1
    os_client.indices.get_mapping.return_value = {
        "project_testp1": {
            "mappings": {
                "properties": {"00080060 Modality_keyword": {"type": "keyword"}}
            }
        }
    }

    mapping = utils.get_field_mapping(os_client, "project_a0841558")

    assert mapping == {"Modality": "00080060 Modality_keyword.keyword"}
