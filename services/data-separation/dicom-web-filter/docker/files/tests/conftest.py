import os
import sys
from pathlib import Path

# Make `app` importable when running pytest from docker/files.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# app.config reads these at import time; no test reaches the services behind them.
for key in (
    "DICOMWEB_BASE_URL",
    "DICOMWEB_BASE_URL_WADO_URI",
    "ACCESS_INFORMATION_INTERFACE_URL",
    "DWF_IDENTITY_OPENID_CONFIG_URL",
    "DWF_IDENTITY_OPENID_CLIENT_ID",
):
    os.environ.setdefault(key, f"http://{key.lower()}")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test@localhost/test")
