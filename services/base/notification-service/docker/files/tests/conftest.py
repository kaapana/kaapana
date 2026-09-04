import os
import sys
import types
from pathlib import Path

# Settings are read at import time; the engine is created but never connected
# (the ASGI test client does not run the lifespan).
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("AII_URL", "http://aii")

# kaapanapy is a shim over kaapana_client that only ships in the base image;
# the routes under test never reach AccessService, so a stub is enough.
_access = types.ModuleType("kaapanapy.services.AccessService")
_access.AccessService = type("AccessService", (), {})
sys.modules.setdefault("kaapanapy", types.ModuleType("kaapanapy"))
sys.modules.setdefault("kaapanapy.services", types.ModuleType("kaapanapy.services"))
sys.modules.setdefault("kaapanapy.services.AccessService", _access)

# Make `app` importable whatever directory pytest is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
