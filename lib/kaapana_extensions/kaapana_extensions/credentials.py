import os
import stat
import json
from pathlib import Path
from typing import Dict, Optional

from kaapana_containers.registries.registry import OCIRegistryDiscovery

_CREDENTIALS_FILE = Path.home() / ".kaapana" / "credentials.json"


def get_credentials() -> Optional[Dict[str, str]]:
    """Load credentials, registry and repo from _CREDENTIALS_FILE.

    Returns:
        Dict with username, password, registry and repo, or None if not found
    """

    if _CREDENTIALS_FILE.exists():
        with open(_CREDENTIALS_FILE) as f:
            return json.load(f)
    return None


def _save_all_credentials(
    username: str, password: str, registry: str, repo: str
) -> None:
    """Save all credentials, registry and repo info to .kaapana/credentials.json.

    WARNING: All data is stored unencrypted on disk!
    Store only in secure locations and protect this file with chmod 600.

    Args:
        username: Registry username
        password: Registry password or token
        registry: Registry URL
        repo: Repository name
    """
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "username": username,
        "password": password,
        "registry": registry,
        "repo": repo,
    }

    with open(_CREDENTIALS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _clear_all_credentials() -> None:
    """Clear saved credentials, registry and repo from .kaapana/credentials.json."""
    if _CREDENTIALS_FILE.exists():
        _CREDENTIALS_FILE.unlink()


def oci_login(registry: str, repo: str, username: str, password: str) -> None:
    """Login to registry and save credentials.

    Args:
        registry: Registry host (e.g., 'registry.hzdr.de')
        repo: Repository name (e.g., 'kaapana/kaapana/extensions')
        username: Username
        password: Password or token

    Raises:
        ValueError: If login fails
    """
    registry_host = registry
    if not registry_host.startswith(("http://", "https://")):
        registry_host = f"https://{registry_host}"

    manager = OCIRegistryDiscovery(
        registry_url=registry_host,
        repository=repo,
        username=username,
        password=password,
    )
    try:
        manager.list_tags()
    except Exception:
        pass    
    manager._request_with_auth_retry("GET", f"{registry_host}/v2/")

    _save_all_credentials(username, password, registry_host, repo)

    os.chmod(_CREDENTIALS_FILE, stat.S_IRUSR | stat.S_IWUSR)


def oci_logout() -> None:
    """Logout and clear saved credentials, registry and repo."""
    _clear_all_credentials()
