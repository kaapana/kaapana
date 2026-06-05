#!/usr/bin/env python3
"""Pull and unpack the Kaapana offline installer payload from an OCI registry.

Install-target counterpart to ``OfflineInstallerHelper.publish_offline_installer``:
pulls ``kaapana/offline-installer:<version>`` and unpacks it into the layout that
``kaapanactl install --offline`` expects -- no Docker daemon required. Credentials
default to ``$KAAPANA_REGISTRY_USERNAME`` / ``$KAAPANA_REGISTRY_PASSWORD``.

Needs the registry client: install ``kaapana-containers`` (pip) or copy
``lib/kaapana_containers/kaapana_containers/registries/registry.py`` next to this
script as ``registry.py``.
"""
import argparse
import os
import sys
import tarfile
import tempfile
from shutil import copy2
from pathlib import Path
from urllib.parse import urlparse


def _normalize_registry_url(raw, scheme="https"):
    p = urlparse(raw.strip() if "://" in raw else f"{scheme}://{raw.strip()}")
    if not p.netloc:
        raise SystemExit(f"Invalid registry URL: {raw!r}")
    return f"{p.scheme}://{p.netloc}"


def _oci_registry_cls():
    here = Path(__file__).resolve().parent
    for path in (None, here, here.parent / "lib" / "kaapana_containers"):
        if path:
            sys.path.insert(0, str(path))
        try:
            # If registry.py is placed next to this script
            if path == here:
                from registry import OCIRegistryDiscovery  # vendored sibling
            else:
                # If its installed as part of kaapana-containers
                from kaapana_containers.registries.registry import OCIRegistryDiscovery
            return OCIRegistryDiscovery
        except ImportError:
            continue
    raise SystemExit(
        "Could not import OCIRegistryDiscovery. Install 'kaapana-containers' or "
        "copy registries/registry.py next to this script as 'registry.py'."
    )


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--registry-url", required=True, help="e.g. https://registry.example.com"
    )
    p.add_argument("--repository", default="kaapana/offline-installer")
    p.add_argument("--tag", required=True, help="Platform version / tag to pull")
    p.add_argument("--target-dir", required=True, type=Path)
    p.add_argument("--username", default=os.environ.get("KAAPANA_REGISTRY_USERNAME"))
    p.add_argument("--password", default=os.environ.get("KAAPANA_REGISTRY_PASSWORD"))
    p.add_argument(
        "--ca-cert", help="CA bundle for TLS verification (HTTPS with a private CA)"
    )
    p.add_argument(
        "--insecure", action="store_true", help="Disable TLS verification (NOT recommended)"
    )
    p.add_argument(
        "--keep-archive", action="store_true", help="Keep the .tar.gz after extraction"
    )
    return p.parse_args(argv)


def _find_archive(download_dir):
    archives = list(Path(download_dir).glob("offline-installer-*.tar.gz"))
    if len(archives) != 1:
        names = ", ".join(path.name for path in archives) or "none"
        raise SystemExit(f"Expected one offline installer archive, found: {names}")
    return archives[0]


def _safe_extract_archive(archive, target_dir):
    with tarfile.open(archive, "r:gz") as tar:
        try:
            tar.extractall(target_dir, filter="data")
        except TypeError:
            tar.extractall(target_dir)


def main(argv=None):
    args = parse_args(argv)
    args.target_dir.mkdir(parents=True, exist_ok=True)

    client = _oci_registry_cls()(
        registry_url=_normalize_registry_url(args.registry_url),
        repository=args.repository.strip(),
        username=args.username.strip() if args.username else None,
        password=args.password.strip() if args.password else None,
    )
    
    if args.insecure:
        client.session.verify = False
    elif args.ca_cert:
        client.session.verify = args.ca_cert

    print(f"Pulling {args.repository}:{args.tag} from {args.registry_url} ...")

    with tempfile.TemporaryDirectory() as download_dir:
        if not client.download_files(args.tag, download_dir):
            raise SystemExit(f"Failed to download {args.repository}:{args.tag}")

        archive = _find_archive(download_dir)
        print(f"Extracting {archive.name} -> {args.target_dir}")
        _safe_extract_archive(archive, args.target_dir)

        if args.keep_archive:
            copy2(archive, args.target_dir / archive.name)

    print(f"Offline installer ready in {args.target_dir}")


if __name__ == "__main__":
    main()
