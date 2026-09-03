import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Make `app` importable when running pytest from docker/files.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The app reads its settings from the environment and opens the database engine at
# import time. The route tests only exercise the handlers, so give them placeholder
# settings and stand in for the database layer; crud is an AsyncMock because the
# handlers await its functions.
for key in (
    "DICOMWEB_BASE_URL",
    "DICOMWEB_BASE_URL_WADO_URI",
    "DATABASE_URL",
    "ACCESS_INFORMATION_INTERFACE_URL",
    "DWF_IDENTITY_OPENID_CONFIG_URL",
    "DWF_IDENTITY_OPENID_CLIENT_ID",
):
    os.environ.setdefault(key, "placeholder")
for name in ("sqlalchemy", "sqlalchemy.ext", "sqlalchemy.ext.asyncio", "app.database"):
    sys.modules[name] = MagicMock()
sys.modules["app.crud"] = AsyncMock()
