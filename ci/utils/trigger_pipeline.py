#!/usr/bin/env python3
"""Trigger a GitLab pipeline via the API with arbitrary variables."""

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Annotated, Optional

import typer


app = typer.Typer(help=__doc__)


def git(*args) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def parse_remote(remote_url: str) -> tuple[str, str]:
    """Return (host_with_scheme, project_path) from a git remote URL."""
    if remote_url.startswith("git@"):
        host, path = remote_url[4:].split(":", 1)
        return f"https://{host}", path.removesuffix(".git")
    parsed = urllib.parse.urlparse(remote_url)
    return f"{parsed.scheme}://{parsed.netloc}", parsed.path.lstrip("/").removesuffix(".git")


def get_token(host: str) -> str:
    """Return token from GITLAB_TOKEN env var or git credential storage."""
    if token := os.environ.get("GITLAB_TOKEN"):
        return token
    parsed = urllib.parse.urlparse(host)
    try:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input=f"protocol={parsed.scheme}\nhost={parsed.netloc}\n\n",
            capture_output=True, text=True, check=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("password="):
                return line.removeprefix("password=")
    except subprocess.CalledProcessError:
        pass
    typer.echo("Error: no token found — set GITLAB_TOKEN or configure git credentials", err=True)
    raise typer.Exit(1)


def post(host: str, project_path: str, token: str, ref: str, variables: dict) -> dict:
    project_id = urllib.parse.quote(project_path, safe="")
    payload = {
        "ref": ref,
        "variables": [{"key": k, "value": v} for k, v in variables.items()],
    }
    req = urllib.request.Request(
        f"{host}/api/v4/projects/{project_id}/pipeline",
        data=json.dumps(payload).encode(),
        headers={"PRIVATE-TOKEN": token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        typer.echo(f"Error {e.code}: {e.read().decode()}", err=True)
        raise typer.Exit(1)


@app.command()
def main(
    variables: Annotated[
        list[str],
        typer.Argument(help="Pipeline variables as KEY=VALUE pairs"),
    ] = [],
    branch: Annotated[
        Optional[str],
        typer.Option("--branch", "-b", help="Branch or tag (default: current git branch)"),
    ] = None,
):
    host, project_path = parse_remote(git("remote", "get-url", "origin"))
    ref = branch or os.environ.get("GITLAB_BRANCH") or git("rev-parse", "--abbrev-ref", "HEAD")
    token = get_token(host)

    parsed_vars = {}
    for var in variables:
        if "=" not in var:
            typer.echo(f"Error: expected KEY=VALUE, got: {var}", err=True)
            raise typer.Exit(1)
        key, _, value = var.partition("=")
        parsed_vars[key] = value

    typer.echo(f"Project : {host}/{project_path}")
    typer.echo(f"Branch  : {ref}")
    if parsed_vars:
        typer.echo("Variables:")
        for k, v in parsed_vars.items():
            typer.echo(f"  {k}={v}")

    result = post(host, project_path, token, ref, parsed_vars)
    typer.echo(f"\nPipeline #{result['id']} created")
    typer.echo(typer.style(result["web_url"], fg=typer.colors.CYAN))


if __name__ == "__main__":
    app()
