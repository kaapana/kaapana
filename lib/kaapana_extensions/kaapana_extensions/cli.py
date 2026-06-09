"""CLI for Kaapana OCI Extension Toolchain."""

import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
from kaapana_containers.registries.registry import OCIError
from kaapana_extensions.credentials import (
    get_credentials,
    oci_login,
    oci_logout,
)
from kaapana_extensions.extensions import ExtensionUtilityLibrary

app = typer.Typer(name="extensionctl", help="OCI Extension Registry CLI for Kaapana")


def _make_client(
    repo: Optional[str],
    registry: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> ExtensionUtilityLibrary:
    """Create an ExtensionUtilityLibrary instance using saved credentials when options are omitted.

    Does not perform any network I/O — use ``async with client:`` to open the connection.
    """
    stored = get_credentials()
    if not repo:
        if stored and stored.get("repo"):
            repo = stored["repo"]
        else:
            typer.echo("Error: --repo is required", err=True)
            raise typer.Exit(1)
    if not registry:
        if stored and stored.get("registry"):
            registry = stored["registry"]
        else:
            typer.echo("Error: --registry is required", err=True)
            raise typer.Exit(1)
    if username is None or password is None:
        if stored and stored.get("username") is not None and "password" in stored:
            username = stored["username"] if username is None else username
            password = stored["password"] if password is None else password
        else:
            typer.echo("Error: --user and --password are required", err=True)
            raise typer.Exit(1)
    return ExtensionUtilityLibrary(registry, repo, username, password)


@app.command(name="login")
def login(
    registry: str = typer.Option(
        ..., "--registry", help="Registry host (e.g., registry.hzdr.de)"
    ),
    repo: str = typer.Option(
        ..., "--repo", help="Repository name (e.g., kaapana/kaapana/extensions)"
    ),
    username: str = typer.Option(..., "--user", help="Username"),
    password: str = typer.Option(..., "--password", help="Password or token"),
):
    """Login to registry and save credentials."""
    try:
        oci_login(registry, repo, username, password)
    except Exception as e:
        typer.echo(f"Error: Login failed - {e}", err=True)
        raise typer.Exit(1)

    typer.echo("")
    typer.echo("┌─────────────────────────────────────────────────────────┐")
    typer.echo("│                    LOGIN SUCCESSFUL                     │")
    typer.echo("├─────────────────────────────────────────────────────────┤")
    typer.echo(f"│  Registry : {registry:<46} │")
    typer.echo(f"│  Username : {username:<46} │")
    typer.echo(f"│  Repository: {repo:<45} │")
    typer.echo("└─────────────────────────────────────────────────────────┘")
    typer.echo("")


@app.command(name="logout")
def logout():
    """Logout from current registry."""
    oci_logout()
    typer.echo("")
    typer.echo("  Logged out successfully")
    typer.echo("")


@app.command(name="whoami")
def whoami():
    """Show current logged in registry."""
    creds = get_credentials()

    if creds:
        username = creds["username"]
        registry = creds["registry"]
        repo = creds["repo"]

        typer.echo("")
        typer.echo("┌─────────────────────────────────────────────────────────┐")
        typer.echo("│                    CURRENT SESSION                      │")
        typer.echo("├─────────────────────────────────────────────────────────┤")
        typer.echo(f"│  Registry   : {registry:<44} │")
        typer.echo(f"│  Username   : {username:<44} │")
        typer.echo(f"│  Repository : {repo:<44} │")
        typer.echo("└─────────────────────────────────────────────────────────┘")
        typer.echo("")
    else:
        typer.echo("")
        typer.echo("  Not logged in")
        typer.echo(
            "  Run: extensionctl login --registry ... --repo ... --user ... --password ..."
        )
        typer.echo("")


@app.command(name="pull")
def pull(
    tag: str = typer.Argument(..., help="Extension tag"),
    output: Path = typer.Argument(
        Path("."), help="Output directory (default: current directory)"
    ),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """Pull extension from registry.

    By default downloads the archive (.tar.gz). Use --extract to unpack.
    """
    client = _make_client(repo, registry, username, password)

    async def _run():
        async with client:
            return await client.pull(tag, output)

    try:
        output_dir = asyncio.run(_run())
    except (OCIError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Pulled: {output_dir}")


@app.command(name="push")
def push(
    source: str = typer.Argument(..., help="Extension tarball (.tar.gz)"),
    bump: Optional[str] = typer.Option(
        None, "--bump", help="Bump version: major, minor, or patch"
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing tag"),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """Push an extension tarball to the registry.

    Only .tar.gz archives are accepted. The tag is always derived from the
    name and version in extension_manifest.json inside the archive.
    """
    ext_path = Path(source)
    if not ext_path.exists():
        typer.echo(f"Error: Source not found: {source}", err=True)
        raise typer.Exit(1)

    client = _make_client(repo, registry, username, password)

    async def _run():
        async with client:
            return await client.push(ext_path, bump=bump, overwrite=overwrite)

    try:
        ext_tag = asyncio.run(_run())
        typer.echo(f"Pushed: {ext_tag}")
    except (OCIError, ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="build")
def build(
    source: str = typer.Argument(
        ...,
        help="Local path or URL[#ref:subdir]  e.g. https://host/repo.git#main:my-ext",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Output directory (archive name is derived from the manifest)",
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Build all extensions in subfolders"
    ),
    push: bool = typer.Option(False, "--push", help="Push to registry after building"),
    bump: Optional[str] = typer.Option(
        None, "--bump", help="(with --push) Bump version: major, minor, or patch"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="(with --push) Overwrite existing tag"
    ),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """Build extension(s) into a .tar.gz archive.

    Source can be a local path or a remote URL with an optional fragment
    specifying the ref and subdirectory, mirroring the Docker URL syntax:

      extensionctl build /path/to/my-ext
      extensionctl build https://host/repo.git
      extensionctl build https://host/repo.git#mybranch
      extensionctl build https://host/repo.git#mybranch:my-ext
      extensionctl build https://host/repo.git#:my-ext

    Add --push to build and push to the registry in one step:

      extensionctl build https://host/repo.git#main:my-ext --push
    """
    try:
        archives = list(ExtensionUtilityLibrary.build(source, output, recursive))
    except (ValueError, RuntimeError, OCIError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    for ext_source, archive in archives:
        typer.echo(f"  Source:  {ext_source}")
        typer.echo(f"  Archive: {archive}")

    if not push:
        return

    client = _make_client(repo, registry, username, password)

    async def _run():
        async with client:
            tags = []
            for _, archive in archives:
                ext_tag = await client.push(archive, bump=bump, overwrite=overwrite)
                typer.echo(f"  Pushed:  {ext_tag}")
                tags.append(ext_tag)
            return tags

    try:
        asyncio.run(_run())
    except (ValueError, RuntimeError, OCIError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="list")
def list_extensions(
    full: bool = typer.Option(
        False, "--full", help="Show full metadata for each extension"
    ),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """List all extensions in repository."""
    client = _make_client(repo, registry, username, password)

    async def _run():
        async with client:
            if not full:
                tags = await client.list_tags()
                if not tags:
                    typer.echo("No extensions found.")
                    return
                for tag in tags:
                    typer.echo(tag)
            else:
                entries = await client.get_all_metadata()
                if not entries:
                    typer.echo("No extensions found.")
                    return
                for _, metadata in entries:
                    typer.echo(json.dumps(metadata, indent=2))

    try:
        asyncio.run(_run())
    except OCIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="info")
def info(
    tag: str = typer.Argument(..., help="Extension tag"),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """[Debug] Show repository/tag, manifest digest, config digest, layer digests, and config JSON."""
    client = _make_client(repo, registry, username, password)

    async def _run():
        async with client:
            return await client.get(tag)

    try:
        config_data = asyncio.run(_run())
    except OCIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(config_data, indent=2))


@app.command(name="delete")
def delete(
    tag: Optional[str] = typer.Argument(
        None, help="Extension tag to delete"
    ),
    all_tags: bool = typer.Option(
        False, "--all", help="Delete all extensions in the repository"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """Delete an extension tag from the registry.

    Delete a single tag:

      extensionctl delete my-extension-v1.0.0

    Delete all tags (with confirmation):

      extensionctl delete --all
      extensionctl delete --all --yes
    """
    if not tag and not all_tags:
        typer.echo("Error: provide a TAG or use --all", err=True)
        raise typer.Exit(1)
    if tag and all_tags:
        typer.echo("Error: --all cannot be combined with a specific tag", err=True)
        raise typer.Exit(1)

    client = _make_client(repo, registry, username, password)

    if tag:
        async def _run():
            async with client:
                await client.delete_tag(tag)

        try:
            asyncio.run(_run())
        except OCIError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
        typer.echo(f"Deleted: {tag}")

    if all_tags:
        async def _list():
            async with client:
                return await client.list_tags()

        try:
            tags = asyncio.run(_list())
        except OCIError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

        if not tags:
            typer.echo("No extensions found.")
            return
        typer.echo(f"Found {len(tags)} extension(s):")
        for t in tags:
            typer.echo(f"  {t}")
        if not yes:
            typer.confirm("\nDelete all of the above?", abort=True)

        async def _delete_all():
            async with client:
                failed = []
                for t in tags:
                    try:
                        await client.delete_tag(t)
                        typer.echo(f"Deleted: {t}")
                    except OCIError as e:
                        typer.echo(f"Failed to delete {t}: {e}", err=True)
                        failed.append(t)
                return failed

        failed = asyncio.run(_delete_all())
        if failed:
            raise typer.Exit(1)


if __name__ == "__main__":
    app()
