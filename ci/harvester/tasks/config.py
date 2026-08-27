"""
Update a single GitLab Runner in config.toml based on its token.
- Reads existing config.toml
- Finds runner by token
- Updates custom_build_dir, limit, request_concurrency, docker volumes
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


def parse_bool(value):
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"expected a boolean, got {value!r}")


def find_runner(runners, token):
    for runner in runners:
        if runner.get("token") == token:
            return runner
    return None


def apply_settings(
    runner, custom_build_dir, limit, request_concurrency, docker_volumes
):
    runner["limit"] = limit
    runner["request_concurrency"] = request_concurrency
    # [runners.custom_build_dir] is a table with an "enabled" key, not a bare bool.
    runner["custom_build_dir"] = {"enabled": custom_build_dir}
    # Volumes live in [runners.docker], which `gitlab-runner register` created
    # for docker executors. Empty list leaves the registered value alone.
    if docker_volumes:
        runner.setdefault("docker", {})["volumes"] = docker_volumes


def main():
    parser = argparse.ArgumentParser(
        description="Update single GitLab Runner in config.toml"
    )
    parser.add_argument("--runner-home", required=True)
    parser.add_argument("--config-path", default=None)
    parser.add_argument(
        "--token", required=True, help="Runner token to identify the runner"
    )
    parser.add_argument("--custom-build-dir", type=parse_bool, default=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--request-concurrency", type=int, default=1)
    parser.add_argument(
        "--docker-volumes",
        default="",
        help="Comma separated docker volumes; empty leaves the registered value alone",
    )
    parser.add_argument("--global-concurrent", type=int, default=None)
    args = parser.parse_args()

    config_path = args.config_path or f"{args.runner_home}/.gitlab-runner/config.toml"
    config = read_config(config_path)

    runner = find_runner(config.get("runners", []), args.token)
    if runner is None:
        raise ValueError(f"No runner found with token: {args.token}")

    apply_settings(
        runner,
        custom_build_dir=args.custom_build_dir,
        limit=args.limit,
        request_concurrency=args.request_concurrency,
        docker_volumes=[v for v in args.docker_volumes.split(",") if v],
    )

    if args.global_concurrent is not None:
        config["concurrent"] = args.global_concurrent

    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(config, f)

    print(f"Runner updated in {config_path}")


if __name__ == "__main__":
    main()
