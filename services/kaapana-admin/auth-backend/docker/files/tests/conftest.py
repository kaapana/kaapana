"""Shared test setup for the auth-backend suite.

Importing the real fastapi/jwt/httpx here (before any test module is collected)
puts them in sys.modules, so test_split_project_prefix's defensive
`sys.modules.setdefault(...)` stubs no-op instead of shadowing the real
packages -- which the TestClient-based tests need. init.py reads the 403 error
page from an absolute container path at import time, so it is stubbed.
"""

import sys
import types
from pathlib import Path

import fastapi  # noqa: F401  force real module into sys.modules
import httpx  # noqa: F401
import jwt  # noqa: F401

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

init_stub = types.ModuleType("init")
init_stub.error_page = "<forbidden>"
sys.modules.setdefault("init", init_stub)
