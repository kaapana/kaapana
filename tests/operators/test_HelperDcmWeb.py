import sys
from pathlib import Path
from unittest.mock import MagicMock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib/kaapana_client"))

from kaapana_client.helper.HelperDcmWeb import HelperDcmWeb


def test_delete_series_skips_series_not_mapped_to_project():
    """dicom-web-filter's 403 for an unmapped series must not abort the delete run."""
    response = MagicMock(status_code=403, text="Series not mapped to project")
    response.raise_for_status.side_effect = requests.HTTPError("403 Client Error")
    helper = HelperDcmWeb(access_token="token")
    helper.session.delete = MagicMock(return_value=response)

    assert helper.delete_series("project-1", "1.2.3", "1.2.3.4") is response
