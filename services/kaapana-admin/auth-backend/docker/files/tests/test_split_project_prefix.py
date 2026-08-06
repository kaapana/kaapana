"""
Unit tests for split_project_prefix, the parser behind the platform-wide
/project/<id>/<service-path> URL convention. It feeds both the OPA policy
input (stripped path) and the AII project resolution (id), so its edge cases
are security-relevant: a wrong split either denies valid requests or evaluates
policies against the wrong path.
No live services: main.py's third-party imports come from the suite's conftest,
or are stubbed below when this file is run on its own.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

# Exactly what main.py imports from outside the stdlib. `setdefault`, not
# assignment: conftest has already put the real jwt/httpx/fastapi in sys.modules
# for a whole-suite run, and its own `init` stub -- init reads the 403.html error
# page from an absolute container path at import time. So these no-op there and
# only take effect when this file is run on its own.
for mod in (
    "jwt",
    "httpx",
    "fastapi",
    "fastapi.responses",
    "init",
):
    sys.modules.setdefault(mod, MagicMock())

from main import split_project_prefix  # noqa: E402


def test_prefixed_path_is_split():
    assert split_project_prefix("/project/abc12345/kaapana-backend/x") == (
        "abc12345",
        "/kaapana-backend/x",
    )


def test_unprefixed_path_passes_through():
    assert split_project_prefix("/kaapana-backend/x") == (None, "/kaapana-backend/x")


def test_none_and_empty_pass_through():
    assert split_project_prefix(None) == (None, None)
    assert split_project_prefix("") == (None, "")


def test_bare_project_id_rest_defaults_to_root():
    # OPA's `requested_prefix == "/"` rule must keep matching.
    assert split_project_prefix("/project/abc12345") == ("abc12345", "/")
    assert split_project_prefix("/project/abc12345/") == ("abc12345", "/")


def test_query_string_is_kept_out_of_the_id_and_preserved():
    assert split_project_prefix(
        "/project/abc12345/data-gallery-ui?limit=10&offset=0"
    ) == (
        "abc12345",
        "/data-gallery-ui?limit=10&offset=0",
    )
    assert split_project_prefix("/project/abc12345?x=1") == ("abc12345", "/?x=1")


def test_empty_id_does_not_match():
    assert split_project_prefix("/project//kaapana-backend/x") == (
        None,
        "/project//kaapana-backend/x",
    )
    assert split_project_prefix("/project/") == (None, "/project/")
    assert split_project_prefix("/project") == (None, "/project")


def test_prefix_must_be_anchored():
    assert split_project_prefix("/foo/project/abc/x") == (None, "/foo/project/abc/x")


def test_id_is_not_url_decoded():
    # An encoded slash stays part of the id; the AII lookup then simply fails,
    # so no project is attached and the path stays unstripped. Not a deny by
    # default -- `admin`'s `^/.*` matches the unstripped path; the guarantee is
    # the missing `Project` header and the service's own 400 (see main.py).
    assert split_project_prefix("/project/a%2Fb/x") == ("a%2Fb", "/x")
