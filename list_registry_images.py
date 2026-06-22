#!/usr/bin/env python3
import re
import requests
import sys

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

GITLAB_URL = "https://codebase.helmholtz.cloud"
REGISTRY_URL = "https://registry.hzdr.de"
PROJECT_PATH = "kaapana/releases"

USERNAME = "mikulas.bankovic"
GITLAB_TOKEN = "glpat-jOrvmw7q-KTdRTbB26BJuW86MQp1OmN3OAk.01.0z0hvxifl"


def get_registry_token(scope):
    resp = requests.get(
        f"{GITLAB_URL}/jwt/auth",
        params={"service": "container_registry", "scope": scope},
        auth=(USERNAME, GITLAB_TOKEN),
    )
    resp.raise_for_status()
    return resp.json()["token"]


def list_repositories():
    encoded_path = PROJECT_PATH.replace("/", "%2F")
    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{encoded_path}/registry/repositories",
            params={"per_page": 100, "page": page},
            headers={"PRIVATE-TOKEN": GITLAB_TOKEN},
        )
        resp.raise_for_status()
        batch = resp.json()
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def list_tags(registry_token, repo_path):
    resp = requests.get(
        f"{REGISTRY_URL}/v2/{repo_path}/tags/list",
        headers={"Authorization": f"Bearer {registry_token}"},
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("tags") or []


def main():
    print("Fetching repository list...")
    try:
        repos = list_repositories()
    except Exception as e:
        print(f"Failed to list repositories: {e}")
        sys.exit(1)
    print(f"Found {len(repos)} images\n")

    for repo in repos:
        repo_path = repo["path"]
        scope = f"repository:{repo_path}:pull"
        try:
            registry_token = get_registry_token(scope)
            tags = [t for t in list_tags(registry_token, repo_path) if SEMVER_RE.match(t)]
            tag_str = ", ".join(sorted(tags)) if tags else "(no semver tags)"
            print(f"{repo_path}")
            print(f"  tags: {tag_str}\n")
        except Exception as e:
            print(f"{repo_path}")
            print(f"  error fetching tags: {e}\n")


if __name__ == "__main__":
    main()
