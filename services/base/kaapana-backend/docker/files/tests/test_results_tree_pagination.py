"""
Regression tests for the lazy results-browser tree pagination.

The `/get-static-website-results-tree` handler pages through one directory
level at a time using MinIO's ``start_after`` (lexicographic, EXCLUSIVE). The
previous code resumed with ``f"{bucket_results_prefix}{continuation_token}0"``
-- a literal ``0`` appended to *every* token. That is only correct for a folder
token (where it is the "next-prefix" boundary that skips the folder's subtree).
For a file token it over-skips: any sibling whose key sorts between the file
key and ``<file key>0`` (e.g. a sibling folder marker with a space/`.`/`-` after
the name -- all below ``0`` = 0x30) is silently dropped from the next page.

The fix (`_results_start_after`) resumes a file token at the exact key and a
folder token at the next-prefix boundary, so it neither skips a sibling nor
re-emits an entry. These tests drive the extracted, un-decorated helpers
(`_list_results_tree_page` + `_results_start_after`) -- the request handler
itself is a MagicMock once fastapi is stubbed.

The MinIO stub honours the S3 ``start_after`` contract: keys are compared
lexicographically and exclusively over the raw key space, then collapsed to
folder markers for ``recursive=False`` -- i.e. the ideal key-ordered listing
that the pagination boundary relies on. That idealization is precisely what
KNOWN LIMITATION 1 below breaks, so these tests pin the boundary arithmetic
only, never the endpoint's behaviour against a real bucket.

KNOWN LIMITATION 1 (pre-existing, NOT fixed here): the real client does not
return a globally key-ordered listing. minio-py 7.2.15's
``parse_list_objects`` builds the object list from ``Contents`` and only then
appends ``CommonPrefixes``, so every file at the level is yielded before every
folder marker. On a directory level that mixes files and folders and exceeds
the page size (default 500) the resume token is therefore not the level's
lexicographic high-water mark, and BOTH failure directions exist:

* ``page_size <= number of .html files at the level`` -- the token is a file
  key, the boundary is that exact key, and every folder whose keys all sort
  BELOW it is DROPPED.
* ``page_size >  number of .html files at the level`` -- the token is a folder
  marker ``F/``, the boundary is the next-prefix ``F0``, which sits above the
  files already emitted on that page, so every such file with a key greater
  than ``F0`` is RE-EMITTED as a duplicate on the next page.

Against ``LEVEL_KEYS`` below under the real ordering: ``page_size=1`` drops
``report-1 final``, and ``page_size=2`` re-emits ``report-1.html`` on page 2
off the ``report-1 final0`` boundary. Both are pre-existing -- develop's
``{token}0`` computes the identical folder boundary (so the duplicate is
bit-identical there) and over-skips a file token even further, dropping
``report-1 final`` *and* ``report-1.html data``. The fix strictly reduces the
loss without eliminating it. Consequently the
``len(names) == len(set(names))`` assertion below holds for the key-ordered
stub but would NOT hold at ``page_size=2`` against the real ordering. Fixing
the ordering needs a client-side merge of the two listings or a switch to
``list_objects_v2`` paging, i.e. a redesign of the endpoint.

KNOWN LIMITATION 2 (pre-existing, NOT fixed here): ``SanitizeQueryParams``
(``app/middlewares.py``, registered in ``app/main.py``) HTML-escapes EVERY
query parameter with no allowlist, and ``continuation_token`` and ``prefix``
are query parameters of ``/get-static-website-results-tree`` (as is
``object_name`` on ``/get-static-website-results-html``). The token is a raw
MinIO object key, so a key containing ``&``, ``'`` or ``"`` comes back escaped
and nothing unescapes it, making the resume boundary the wrong key -- too low
for e.g. ``&b`` (``&amp;b`` sorts below ``&b`` -> duplicates), too high for
``&B`` (-> dropped siblings). An escaped ``prefix`` matches no key at all, so
such a folder cannot be expanded. Develop's relative-path token was equally
escapable; the fix belongs on the middleware (an allowlist / opt-out), not in a
per-parameter patch here.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

for mod in (
    "app.config",
    "app.dependencies",
    "app.workflows.utils",
    "fastapi",
    "fastapi.responses",
    "jwt",
    "minio",
    "minio.error",
    "starlette",
    "starlette.responses",
    "opensearchpy",
    "requests",
):
    sys.modules.setdefault(mod, MagicMock())

import app.admin.routers as routers  # noqa: E402


class _Obj:
    def __init__(self, object_name):
        self.object_name = object_name


class FakeMinio:
    """MinIO stub honouring prefix + recursive=False (delimiter collapse) +
    start_after (lexicographic, exclusive) over a flat set of raw object keys."""

    def __init__(self, keys):
        self._keys = sorted(keys)

    def list_objects(self, bucket, prefix="", recursive=False, start_after=None):
        emitted = set()
        for key in self._keys:
            if not key.startswith(prefix):
                continue
            if start_after is not None and not key > start_after:
                continue
            rest = key[len(prefix) :]
            if not recursive and "/" in rest:
                name = prefix + rest.split("/", 1)[0] + "/"
            else:
                name = key
            if name in emitted:
                continue
            emitted.add(name)
            yield _Obj(name)


# One directory level. "report-1.html data/" is the sibling that sorts between
# the file key "report-1.html" and "report-1.html0" (the old boundary).
LEVEL_KEYS = [
    "report-1 final/index.html",  # folder "report-1 final"
    "report-1.html",  # file  "report-1.html"
    "report-1.html data/x.png",  # folder "report-1.html data"  <- the gap sibling
    "report-1/index.html",  # folder "report-1"
    "report-2/index.html",  # folder "report-2"
]


def _collect_all_pages(minio, results_prefix, relative_prefix, page_size):
    """Page through the whole level exactly as the handler does, returning the
    concatenated item names in order."""
    names = []
    token = None
    seen_pages = 0
    while True:
        start_after = routers._results_start_after(token) if token else None
        objects = minio.list_objects(
            "bucket", prefix=results_prefix, recursive=False, start_after=start_after
        )
        items, token = routers._list_results_tree_page(
            objects, results_prefix, relative_prefix, page_size, lambda name: name
        )
        names.extend(item["name"] for item in items)
        seen_pages += 1
        assert seen_pages < 20, "pagination did not terminate"
        if not token:
            break
    return names


def test_no_sibling_is_skipped_or_re_emitted_across_pages():
    minio = FakeMinio(LEVEL_KEYS)

    names = _collect_all_pages(
        minio, results_prefix="", relative_prefix="", page_size=2
    )

    # Every entry appears exactly once: nothing skipped, nothing duplicated.
    assert names == [
        "report-1 final",
        "report-1.html",
        "report-1.html data",
        "report-1",
        "report-2",
    ]
    assert len(names) == len(set(names))

    # The three keys called out in the bug report all survive the page boundary.
    for survivor in ("report-1", "report-1.html", "report-1 final"):
        assert survivor in names


def test_old_zero_boundary_would_have_dropped_the_gap_sibling():
    """Pins the actual regression: page 1 ends on the file 'report-1.html', and
    the old boundary '<key>0' excludes the 'report-1.html data/' sibling."""
    minio = FakeMinio(LEVEL_KEYS)

    old_start_after = "report-1.html" + "0"  # previous behaviour
    old_next = [
        o.object_name
        for o in minio.list_objects("b", prefix="", start_after=old_start_after)
    ]
    assert "report-1.html data/" not in old_next  # dropped by the old code

    fixed_start_after = routers._results_start_after("report-1.html")
    fixed_next = [
        o.object_name
        for o in minio.list_objects("b", prefix="", start_after=fixed_start_after)
    ]
    assert "report-1.html data/" in fixed_next  # kept by the fix


def test_start_after_file_key_resumes_exactly():
    # start_after is already exclusive, so an exact file key does not re-emit it.
    assert routers._results_start_after("a/b/report-1.html") == "a/b/report-1.html"


def test_start_after_folder_marker_skips_subtree_without_touching_siblings():
    boundary = routers._results_start_after("a/b/report-1/")
    assert boundary == "a/b/report-10"
    # every child of the folder sorts below the boundary -> subtree skipped,
    assert "a/b/report-1/index.html" < boundary
    # the folder marker itself sorts below it -> not re-emitted,
    assert "a/b/report-1/" < boundary
    # but an unrelated sibling stays above it -> not dropped.
    assert "a/b/report-2/" > boundary
