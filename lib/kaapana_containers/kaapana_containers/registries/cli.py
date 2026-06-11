import asyncio
import json
import os
from functools import wraps
from typing import Optional, List
import typer
from kaapana_containers.registries.registry import OCIError, OCIRegistryDiscovery

app = typer.Typer(help="OCI Registry Discovery CLI")


def _load_json(json_str_or_path: str) -> dict:
    if os.path.isfile(json_str_or_path):
        with open(json_str_or_path, "r") as f:
            return json.load(f)
    try:
        return json.loads(json_str_or_path)
    except json.JSONDecodeError:
        typer.echo("Error: Invalid JSON input.", err=True)
        raise typer.Exit(1)


def _make_client(
    registry_url: str, repository: str, username: Optional[str], password: Optional[str]
) -> OCIRegistryDiscovery:
    return OCIRegistryDiscovery(
        registry_url, repository, username=username, password=password
    )


def _async_command(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


@app.command()
@_async_command
async def publish(
    registry_url: str = typer.Argument(
        ..., help="Base registry URL (e.g., https://ghcr.io)"
    ),
    repository: str = typer.Argument(..., help="Repository path (e.g., user/project)"),
    tag: str = typer.Argument(..., help="Tag to publish"),
    metadata_json: str = typer.Argument(..., help="Metadata JSON string or path"),
    files: Optional[List[str]] = typer.Option(
        None, help="Optional list of files to include"
    ),
    username: Optional[str] = typer.Option(None, help="Username for authentication"),
    password: Optional[str] = typer.Option(None, help="Password for authentication"),
):
    """Publish metadata and optional files to the registry under a specific tag."""
    metadata = _load_json(metadata_json)
    client = _make_client(registry_url, repository, username, password)
    try:
        async with client:
            success = await client.create_or_update_tag(tag, metadata, files)
    except OCIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if success:
        typer.echo(f"Successfully published tag '{tag}' to {repository}")
    else:
        typer.echo(f"Failed to publish tag '{tag}'", err=True)
        raise typer.Exit(1)


@app.command()
@_async_command
async def list_tags(
    registry_url: str = typer.Argument(...),
    repository: str = typer.Argument(...),
    username: Optional[str] = typer.Option(None),
    password: Optional[str] = typer.Option(None),
):
    """List all tags in a repository."""
    client = _make_client(registry_url, repository, username, password)
    try:
        async with client:
            tags = await client.list_tags()
    except OCIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if tags:
        typer.echo(f"Tags in {repository}:")
        for tag in tags:
            typer.echo(f"- {tag}")
    else:
        typer.echo("No tags found.")


@app.command()
@_async_command
async def metadata(
    registry_url: str = typer.Argument(...),
    repository: str = typer.Argument(...),
    tag: Optional[str] = typer.Argument(None, help="Specific tag (optional)"),
    download_dir: Optional[str] = typer.Option(
        None, help="Download directory for associated files"
    ),
    username: Optional[str] = typer.Option(None),
    password: Optional[str] = typer.Option(None),
):
    """Show metadata for a specific tag or all tags in a repository."""
    client = _make_client(registry_url, repository, username, password)
    try:
        async with client:
            metadata_list = await client.get_all_metadata(tag)
            if not metadata_list:
                typer.echo("No metadata found.")
                raise typer.Exit(1)
            for tag_name, data in metadata_list:
                typer.echo(f"\nTag: {tag_name}")
                typer.echo(json.dumps(data, indent=2))
                if download_dir:
                    typer.echo(f"Downloading files for {tag_name}...")
                    tag_dir = (
                        os.path.join(download_dir, tag_name) if not tag else download_dir
                    )
                    await client.download_files(tag_name, tag_dir)
    except typer.Exit:
        raise
    except OCIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
@_async_command
async def delete(
    registry_url: str = typer.Argument(...),
    repository: str = typer.Argument(...),
    tag: str = typer.Argument(...),
    username: Optional[str] = typer.Option(None),
    password: Optional[str] = typer.Option(None),
):
    """Delete a specific tag from the repository."""
    client = _make_client(registry_url, repository, username, password)
    try:
        async with client:
            success = await client.delete_tag(tag)
    except OCIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if success:
        typer.echo(f"Successfully deleted tag '{tag}' from {repository}")
    else:
        typer.echo(f"Failed to delete tag '{tag}'", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
