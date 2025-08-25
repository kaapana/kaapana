import typer
import json
import os
from typing import Optional, List
from kaapana_oci.registry import OCIRegistryDiscovery

app = typer.Typer(help="OCI Registry Discovery CLI")


def _load_json(json_str_or_path: str) -> dict:
    if os.path.isfile(json_str_or_path):
        with open(json_str_or_path, "r") as f:
            return json.load(f)
    try:
        return json.loads(json_str_or_path)
    except json.JSONDecodeError:
        typer.echo("❌ Error: Invalid JSON input.", err=True)
        raise typer.Exit(1)


def _init_client(
    registry_url: str, repository: str, username: Optional[str], password: Optional[str]
) -> OCIRegistryDiscovery:
    return OCIRegistryDiscovery(
        registry_url, repository, username=username, password=password
    )


@app.command()
def publish(
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
    """
    Publish metadata and optional files to the registry under a specific tag.
    """
    metadata = _load_json(metadata_json)
    client = _init_client(registry_url, repository, username, password)
    success = client.create_or_update_tag(tag, metadata, files)
    if success:
        typer.echo(f"✅ Successfully published tag '{tag}' to {repository}")
    else:
        typer.echo(f"❌ Failed to publish tag '{tag}'", err=True)
        raise typer.Exit(1)


@app.command()
def list_tags(
    registry_url: str,
    repository: str,
    username: Optional[str] = typer.Option(None),
    password: Optional[str] = typer.Option(None),
):
    """
    List all tags in a repository.
    """
    client = _init_client(registry_url, repository, username, password)
    tags = client.list_tags()
    if tags:
        typer.echo(f"📦 Tags in {repository}:")
        for tag in tags:
            typer.echo(f"- {tag}")
    else:
        typer.echo("⚠️ No tags found.")


@app.command()
def metadata(
    registry_url: str,
    repository: str,
    tag: Optional[str] = typer.Argument(None, help="Specific tag (optional)"),
    download_dir: Optional[str] = typer.Option(
        None, help="Download directory for associated files"
    ),
    username: Optional[str] = typer.Option(None),
    password: Optional[str] = typer.Option(None),
):
    """
    Show metadata for a specific tag or all tags in a repository.
    """
    client = _init_client(registry_url, repository, username, password)
    metadata_list = client.get_all_metadata(tag)

    if not metadata_list:
        typer.echo("⚠️ No metadata found.")
        raise typer.Exit(1)

    for tag_name, data in metadata_list:
        typer.echo(f"\n🔖 Tag: {tag_name}")
        typer.echo(json.dumps(data, indent=2))

        if download_dir:
            typer.echo(f"📥 Downloading files for {tag_name}...")
            tag_dir = os.path.join(download_dir, tag_name) if not tag else download_dir
            client.download_files(repository, tag_name, tag_dir)


@app.command()
def delete(
    registry_url: str,
    repository: str,
    tag: str,
    username: Optional[str] = typer.Option(None),
    password: Optional[str] = typer.Option(None),
):
    """
    Delete a specific tag from the repository.
    """
    client = _init_client(registry_url, repository, username, password)
    success = client.delete_tag(tag)
    if success:
        typer.echo(f"🗑️ Successfully deleted tag '{tag}' from {repository}")
    else:
        typer.echo(f"❌ Failed to delete tag '{tag}'", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
