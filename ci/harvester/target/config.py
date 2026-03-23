#!/usr/bin/env python3
"""
Update a single GitLab Runner in config.toml based on its token.
- Reads existing config.toml
- Finds runner by token
- Updates custom_build_dir (as list of tables), limit, request_concurrency
- Writes updated TOML back
"""

import argparse
from pathlib import Path
import tomli
import tomli_w

def read_config(path):
    path = Path(path)
    if path.exists():
        with path.open("rb") as f:
            return tomli.load(f)
    return {}

def update_runner_by_token(runners, token, updates):
    """
    Update the runner matching the token.
    custom_build_dir must be a table: [runners.custom_build_dir]
    """
    for r in runners:
        if r.get("token") == token:
            cbd_value = updates.pop("custom_build_dir", None)
            if cbd_value is not None:
                r["custom_build_dir"] = {"enabled": bool(cbd_value)}  # <-- table, not list
            # Update remaining keys
            for k, v in updates.items():
                r[k] = v
            return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Update single GitLab Runner in config.toml")
    parser.add_argument("--runner-home", required=True)
    parser.add_argument("--config-path", default=None)
    parser.add_argument("--token", required=True, help="Runner token to identify the runner")
    parser.add_argument("--custom-build-dir", type=bool, default=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--request-concurrency", type=int, default=1)
    parser.add_argument("--global-concurrent", type=int, default=None)
    args = parser.parse_args()

    config_path = args.config_path or f"{args.runner_home}/.gitlab-runner/config.toml"
    config = read_config(config_path)

    # Ensure runners list exists
    config.setdefault("runners", [])

    # Update the runner matching the token
    updated = update_runner_by_token(
        config["runners"],
        args.token,
        {
            "custom_build_dir": args.custom_build_dir,
            "limit": args.limit,
            "request_concurrency": args.request_concurrency
        }
    )

    if not updated:
        raise ValueError(f"No runner found with token: {args.token}")

    # Update global concurrent if provided
    if args.global_concurrent is not None:
        config["concurrent"] = args.global_concurrent

    # Write updated TOML back
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(config, f)

    print(f"Runner updated in {config_path}")

if __name__ == "__main__":
    main()