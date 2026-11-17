#!/usr/bin/env python3
"""Pick the docker.io account from DOCKER_IO_CONFIG with the most pulls left.

DOCKER_IO_CONFIG is a File-type variable, its file holds a JSON object of
docker.io users to tokens. Prints the chosen user on the first line and its
token on the second, or nothing when no account is usable. The caller reads
both lines as data:

    mapfile -t docker_io < <(python3 select_docker_io_credential.py)
    export DOCKER_IO_USER="${docker_io[0]:-}" DOCKER_IO_PASSWORD="${docker_io[1]:-}"

The report goes to stderr and never contains a token. The exit code is always 0,
so a Docker Hub outage falls back to anonymous pulls instead of failing the job.
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

AUTH_URL = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull"
RATELIMIT_URL = "https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest"
TIMEOUT_SECONDS = 20


def report(message: str) -> None:
    print(f"docker.io: {message}", file=sys.stderr)


def read_config(path: str) -> str:
    if not path:
        return ""
    try:
        return Path(path).read_text().strip()
    except OSError:
        report("WARNING: the DOCKER_IO_CONFIG file cannot be read.")
        return ""


def parse_config(raw: str) -> dict[str, str]:
    config = json.loads(raw)
    if not isinstance(config, dict) or not config:
        raise ValueError("not a non-empty JSON object")
    if not all(user and isinstance(token, str) and token for user, token in config.items()):
        raise ValueError("every user needs a non-empty token")
    if any("\n" in user + token for user, token in config.items()):
        raise ValueError("users and tokens must be single lines")
    return config


def remaining_pulls(user: str, token: str) -> int | None:
    basic = base64.b64encode(f"{user}:{token}".encode()).decode()
    request = urllib.request.Request(AUTH_URL, headers={"Authorization": f"Basic {basic}"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        bearer = json.load(response)["token"]
    request = urllib.request.Request(RATELIMIT_URL, method="HEAD", headers={"Authorization": f"Bearer {bearer}"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        remaining = response.headers.get("ratelimit-remaining")
    return None if remaining is None else int(remaining.split(";")[0])


def select(accounts: dict[str, str]) -> tuple[str, str] | None:
    best, best_remaining = None, 0
    for user, token in accounts.items():
        try:
            remaining = remaining_pulls(user, token)
        except (OSError, ValueError, KeyError):
            report(f"'{user}' was rejected or Docker Hub is unreachable, skipped.")
            continue
        if remaining is None:
            report(f"'{user}' has no pull limit.")
            return user, token
        report(f"'{user}' has {remaining} pulls left.")
        if remaining > best_remaining:
            best, best_remaining = (user, token), remaining
    return best


def chosen_account(raw_config: str) -> tuple[str, str] | None:
    if not raw_config:
        report("DOCKER_IO_CONFIG is empty, pulling anonymously.")
        return None
    try:
        accounts = parse_config(raw_config)
    except ValueError:
        report("WARNING: DOCKER_IO_CONFIG is not a JSON object of users to tokens, pulling anonymously.")
        return None
    chosen = select(accounts)
    if chosen is None:
        report("WARNING: no account in DOCKER_IO_CONFIG is usable, pulling anonymously.")
        return None
    report(f"using '{chosen[0]}'.")
    return chosen


def main() -> int:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    chosen = chosen_account(read_config(os.environ.get("DOCKER_IO_CONFIG", "")))
    if chosen is not None:
        print("\n".join(chosen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
