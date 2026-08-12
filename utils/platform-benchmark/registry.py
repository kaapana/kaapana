"""Push/pull tagged benchmark results to the GitLab generic package registry,
so every MR's numbers are kept centrally instead of living only on whichever
runner produced them — a later pipeline can pull the full history back down
to build the report's cross-MR view.

Auth: CI_JOB_TOKEN when running inside a GitLab CI job, else GITLAB_TOKEN for
manual/local use. Project + API host default to this repo's own CI
variables, overridable via GITLAB_PROJECT_ID / GITLAB_API_URL when running
outside CI.
"""

from __future__ import annotations

import os

import requests

import store

PACKAGE_NAME = "kaapana-benchmark-results"


def _api_url() -> str:
    return os.environ.get("GITLAB_API_URL") or os.environ.get(
        "CI_API_V4_URL", "https://codebase.helmholtz.cloud/api/v4")


def _project_id() -> str:
    project_id = os.environ.get("GITLAB_PROJECT_ID") or os.environ.get("CI_PROJECT_ID")
    if not project_id:
        raise SystemExit("set GITLAB_PROJECT_ID (or run inside CI, where CI_PROJECT_ID "
                          "is set automatically)")
    return project_id


def _headers() -> dict:
    if job_token := os.environ.get("CI_JOB_TOKEN"):
        return {"JOB-TOKEN": job_token}
    if token := os.environ.get("GITLAB_TOKEN"):
        return {"PRIVATE-TOKEN": token}
    raise SystemExit("set CI_JOB_TOKEN (inside CI) or GITLAB_TOKEN (locally) to reach "
                      "the package registry")


def _package_url(tag: str) -> str:
    return f"{_api_url()}/projects/{_project_id()}/packages/generic/{PACKAGE_NAME}/{tag}/{tag}.json"


def push(tag: str) -> None:
    """Upload a locally stored tag's result to the registry."""
    path = store.RESULTS_DIR / f"{tag}.json"
    if not path.exists():
        raise SystemExit(f"no local result for tag {tag!r} at {path}")
    resp = requests.put(_package_url(tag), headers=_headers(), data=path.read_bytes(), timeout=30)
    resp.raise_for_status()


def pull(tag: str, force: bool = False) -> bool:
    """Download a tag into the local results dir. Returns False without
    touching anything if it's already present (unless force) or the
    registry has nothing under that tag."""
    path = store.RESULTS_DIR / f"{tag}.json"
    if path.exists() and not force:
        return False
    resp = requests.get(_package_url(tag), headers=_headers(), timeout=30)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    store.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(resp.content)
    return True


def list_tags() -> list[str]:
    """Every tag ever pushed, oldest first."""
    tags: list[str] = []
    page = 1
    while True:
        resp = requests.get(
            f"{_api_url()}/projects/{_project_id()}/packages",
            headers=_headers(),
            params={"package_name": PACKAGE_NAME, "per_page": 100, "page": page,
                    "order_by": "created_at", "sort": "asc"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            return tags
        tags += [p["version"] for p in batch]
        page += 1


def pull_all() -> list[str]:
    """Pull every tag not already present locally. Returns the newly-fetched ones."""
    return [tag for tag in list_tags() if pull(tag)]
