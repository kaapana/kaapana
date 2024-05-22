import sys
from unittest.mock import MagicMock


def mock_modules():
    sys.modules["opensearchpy"] = MagicMock()
