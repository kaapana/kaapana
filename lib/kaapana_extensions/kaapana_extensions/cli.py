"""CLI for Kaapana OCI Extension Toolchain."""

import json
from pathlib import Path
from typing import Optional
import typer
from kaapana_extensions.credentials import (
    get_credentials,
    oci_login,
    oci_logout,
)
from kaapana_extensions.extensions import ExtensionUtilityLibrary

app = typer.Typer(name="extensionctl", help="OCI Extension Registry CLI for Kaapana")


def _complete_tags(incomplete: str):
    """Return matching registry tags for shell completion."""
    try:
        creds = get_credentials()
        if not creds:
            return []
        client = ExtensionUtilityLibrary(
            creds["registry"], creds["repo"], creds["username"], creds["password"]
        )
        return [t for t in client.list_extensions() if t.startswith(incomplete)]
    except Exception:
        return []


def _get_client(
    repo: Optional[str],
    registry: Optional[str],
    username: Optional[str],
    password: Optional[str],
):
    """Create ExtensionUtilityLibrary client, using saved credentials when options are omitted."""
    # If repo or registry not provided, try to load from stored credentials
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
    # Use stored username/password if not supplied
    if not username or not password:
        if stored and stored.get("username") and stored.get("password"):
            username = username or stored["username"]
            password = password or stored["password"]
        else:
            typer.echo("Error: --user and --password are required", err=True)
            raise typer.Exit(1)
    client = ExtensionUtilityLibrary(registry, repo, username, password)
    return client


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
    tag: str = typer.Argument(..., help="Extension tag", autocompletion=_complete_tags),
    output: Path = typer.Argument(Path("."), help="Output directory (default: current directory)"),
    extract: bool = typer.Option(
        False, "--extract", help="Also extract the archive into output/<tag>/"
    ),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """Pull extension from registry.

    By default downloads the archive (.tar.gz). Use --extract to unpack.
    """
    client = _get_client(repo, registry, username, password)
    archive = client.pull(tag, output, extract=extract)
    typer.echo(f"Pulled: {archive}")
    if extract:
        typer.echo(f"Extracted: {archive.parent / tag}/")


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
    client = _get_client(repo, registry, username, password)
    ext_path = Path(source)
    if not ext_path.exists():
        typer.echo(f"Error: Source not found: {source}", err=True)
        raise typer.Exit(1)
    try:
        ext_tag = client.push(ext_path, bump=bump, overwrite=overwrite)
        typer.echo(f"Pushed: {ext_tag}")
    except (ValueError, RuntimeError) as e:
        typer.echo(f"{e}", err=True)
        raise typer.Exit(1)


@app.command(name="build")
def build(
    source: str = typer.Argument(
        ...,
        help="Local path or git+URL[@ref][#subdir]  e.g. git+https://host/repo.git@main#my-ext",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Output directory (archive name is derived from the manifest)",
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Build all extensions in subfolders"
    ),
):
    """Build extension(s) into a .tar.gz archive.

    Source can be a local directory or a git URL with optional ref and subdir:

      extensionctl build /path/to/my-ext
      extensionctl build git+https://host/repo.git@main#my-ext
      extensionctl build git+https://host/repo.git -r
    """
    try:
        for ext_source, archive in ExtensionUtilityLibrary.build(source, output, recursive):
            typer.echo(f"  Source:  {ext_source}")
            typer.echo(f"  Archive: {archive}")
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="publish")
def publish(
    source: str = typer.Argument(
        ...,
        help="Local path or git+URL[@ref][#subdir]  e.g. git+https://host/repo.git@main#my-ext",
    ),
    bump: Optional[str] = typer.Option(
        None, "--bump", help="Auto-increment version: major, minor, or patch"
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing tag"),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Publish all extensions in subfolders"
    ),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """Build and push extension(s) to the registry.

    Source can be a local directory or a git URL with optional ref and subdir:

      extensionctl publish /path/to/my-ext
      extensionctl publish git+https://host/repo.git@main#my-ext
      extensionctl publish git+https://host/repo.git -r
    """
    client = _get_client(repo, registry, username, password)
    try:
        for ext_source, ext_tag in client.publish(source, recursive=recursive, bump=bump, overwrite=overwrite):
            typer.echo(f"  Source:    {ext_source}")
            typer.echo(f"  Published: {ext_tag}")
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="list")
def list_extensions(
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """List all extensions in repository."""
    client = _get_client(repo, registry, username, password)
    tags = client.list_extensions()
    if not tags:
        typer.echo("No extensions found.")
        return
    for tag in tags:
        typer.echo(tag)


@app.command(name="info")
def info(
    tag: str = typer.Argument(..., help="Extension tag", autocompletion=_complete_tags),
    repo: Optional[str] = typer.Option(None, "--repo"),
    registry: Optional[str] = typer.Option(None, "--registry"),
    username: Optional[str] = typer.Option(None, "--user"),
    password: Optional[str] = typer.Option(None, "--password"),
):
    """[Debug] Show repository/tag, manifest digest, config digest, layer digests, and config JSON."""
    client = _get_client(repo, registry, username, password)
    config_data = client._manager.get(tag)
    if config_data:
        typer.echo("Config:")
        typer.echo(json.dumps(config_data, indent=2))


@app.command(name="delete")
def delete(
    tag: Optional[str] = typer.Argument(
        None, help="Extension tag to delete", autocompletion=_complete_tags
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

    client = _get_client(repo, registry, username, password)

    if all_tags:
        tags = client.list_extensions()
        if not tags:
            typer.echo("No extensions found.")
            return
        typer.echo(f"Found {len(tags)} extension(s):")
        for t in tags:
            typer.echo(f"  {t}")
        if not yes:
            typer.confirm("\nDelete all of the above?", abort=True)
        failed = []
        for t in tags:
            if client.delete_extension(t):
                typer.echo(f"Deleted: {t}")
            else:
                typer.echo(f"Failed to delete: {t}", err=True)
                failed.append(t)
        if failed:
            raise typer.Exit(1)
    else:
        success = client.delete_extension(tag)
        if success:
            typer.echo(f"Deleted: {tag}")
        else:
            typer.echo(f"Failed to delete: {tag}", err=True)
            raise typer.Exit(1)


app()
