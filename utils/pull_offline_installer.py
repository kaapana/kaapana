#!/usr/bin/env python3
"""Pull and unpack the Kaapana offline installer payload from an OCI registry.

Install-target counterpart to ``OfflineInstallerHelper.publish_offline_installer``:
pulls ``offline-installer:<version>`` and unpacks it into the layout that
``kaapanactl install --offline`` expects -- no Docker daemon required. Credentials
default to ``$KAAPANA_REGISTRY_USERNAME`` / ``$KAAPANA_REGISTRY_PASSWORD``.

Self-contained by design: this runs on a bare install target before anything is
provisioned, so it uses the standard library only. Copy this single file over and
run it with the system ``python3``. The pull half of the OCI protocol is mirrored
from ``lib/kaapana_containers/kaapana_containers/registries/registry.py`` -- keep
the two in sync if the publish side changes.
"""

import argparse
import json
import os
import re
import ssl
import tarfile
import tempfile
import urllib.error
import urllib.request
from base64 import b64encode
from pathlib import Path
from shutil import copy2
from urllib.parse import urlencode, urlparse

MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"


def _normalize_registry_url(raw, scheme="https"):
    p = urlparse(raw.strip() if "://" in raw else f"{scheme}://{raw.strip()}")
    if not p.netloc:
        raise SystemExit(f"Invalid registry URL: {raw!r}")
    return f"{p.scheme}://{p.netloc}"


def _oci_error(url, err):
    """Render an OCI error body ({"errors": [{code, message}]}) as a SystemExit."""
    detail = f"HTTP {err.code}"
    try:
        errors = json.loads(err.read().decode()).get("errors") or []
        if errors:
            detail = f"{errors[0].get('code', detail)}: {errors[0].get('message', '')}".strip(
                ": "
            )
    except (ValueError, OSError):
        pass
    return SystemExit(f"Registry request failed ({url}): {detail}")


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Blob GETs redirect to signed storage URLs that reject a forwarded Authorization header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urlparse(newurl).netloc != urlparse(req.full_url).netloc:
            new.remove_header("Authorization")
        return new


class _OCIPull:
    """Read-only OCI registry client: enough of the protocol to fetch a tag's files."""

    def __init__(
        self, registry_url, repository, username=None, password=None, ssl_context=None
    ):
        self.registry_url = registry_url.rstrip("/")
        self.repository = repository
        self.username = username
        self.password = password
        self.bearer_token = None
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_context),
            _StripAuthOnRedirect(),
        )

    def _basic_auth_header(self):
        if self.username and self.password:
            token = b64encode(f"{self.username}:{self.password}".encode()).decode()
            return f"Basic {token}"
        return None

    def _auth_header(self):
        if self.bearer_token:
            return f"Bearer {self.bearer_token}"
        return self._basic_auth_header()

    def _open(self, url, accept=None):
        req = urllib.request.Request(url)
        if accept:
            req.add_header("Accept", accept)
        auth = self._auth_header()
        if auth:
            req.add_header("Authorization", auth)
        try:
            with self._opener.open(req) as resp:
                return resp.read()
        except urllib.error.HTTPError:
            raise  # handled by the caller's auth retry
        except urllib.error.URLError as err:
            raise SystemExit(f"Cannot reach {url}: {err.reason}") from err

    def _get_bearer_token(self, www_auth):
        match = re.match(
            r'Bearer realm="([^"]+)",service="([^"]+)"(?:,scope="([^"]+)")?', www_auth
        )
        if not match:
            raise SystemExit(f"Cannot parse WWW-Authenticate header: {www_auth!r}")
        realm, service, scope = match.groups()
        params = {"service": service}
        if scope:
            params["scope"] = scope

        req = urllib.request.Request(f"{realm}?{urlencode(params, safe=':/')}")
        basic = self._basic_auth_header()
        if basic:
            req.add_header("Authorization", basic)
        try:
            with self._opener.open(req) as resp:
                token = json.loads(resp.read().decode()).get("token")
        except urllib.error.HTTPError as err:
            raise SystemExit(
                f"Token endpoint {realm} returned HTTP {err.code}"
            ) from err
        except urllib.error.URLError as err:
            raise SystemExit(
                f"Cannot reach token endpoint {realm}: {err.reason}"
            ) from err
        if not token:
            raise SystemExit(f"Token endpoint {realm} did not return a token")
        return token

    def _request_with_auth_retry(self, url, accept=None):
        try:
            return self._open(url, accept)
        except urllib.error.HTTPError as err:
            www_auth = err.headers.get("WWW-Authenticate") if err.code == 401 else None
            if not www_auth:
                raise _oci_error(url, err) from err
            self.bearer_token = self._get_bearer_token(www_auth)
        try:
            return self._open(url, accept)
        except urllib.error.HTTPError as err:
            raise _oci_error(url, err) from err

    def get(self, tag):
        """Return the metadata stored in the tag's config blob."""
        url = f"{self.registry_url}/v2/{self.repository}/manifests/{tag}"
        try:
            config_digest = json.loads(
                self._request_with_auth_retry(url, MANIFEST_MEDIA_TYPE)
            )["config"]["digest"]
        except (ValueError, KeyError) as exc:
            raise SystemExit(
                f"Cannot parse manifest for {self.repository}:{tag}: {exc}"
            ) from exc

        blob = self._request_with_auth_retry(
            f"{self.registry_url}/v2/{self.repository}/blobs/{config_digest}"
        )
        try:
            return json.loads(blob)
        except ValueError as exc:
            raise SystemExit(
                f"Config blob for {self.repository}:{tag} is not valid JSON: {exc}"
            ) from exc

    def download_files(self, tag, output_dir):
        metadata = self.get(tag)
        files = metadata.get("files")
        if not files:
            raise SystemExit(f"No files associated with {self.repository}:{tag}")

        safe_root = Path(output_dir).resolve()
        safe_root.mkdir(parents=True, exist_ok=True)
        for file_info in files:
            filename = file_info["filename"]
            dest = (safe_root / filename).resolve()
            if not dest.is_relative_to(safe_root):
                raise SystemExit(
                    f"Refusing filename from registry metadata: {filename!r}"
                )
            blob_url = (
                f"{self.registry_url}/v2/{self.repository}/blobs/{file_info['digest']}"
            )
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(self._request_with_auth_retry(blob_url))


def _ssl_context(insecure, ca_cert):
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if ca_cert:
        return ssl.create_default_context(cafile=ca_cert)
    return None


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--registry-url", required=True, help="e.g. https://registry.example.com"
    )
    p.add_argument("--repository", default="offline-installer")
    p.add_argument("--tag", required=True, help="Platform version / tag to pull")
    p.add_argument("--target-dir", required=True, type=Path)
    p.add_argument("--username", default=os.environ.get("KAAPANA_REGISTRY_USERNAME"))
    p.add_argument("--password", default=os.environ.get("KAAPANA_REGISTRY_PASSWORD"))
    p.add_argument(
        "--ca-cert", help="CA bundle for TLS verification (HTTPS with a private CA)"
    )
    p.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification (NOT recommended)",
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
            target_dir = Path(target_dir).resolve()
            for member in tar.getmembers():
                target_path = (target_dir / member.name).resolve()
                if (
                    not target_path.is_relative_to(target_dir)
                    or member.issym()
                    or member.islnk()
                ):
                    raise SystemExit(f"Refusing unsafe archive member: {member.name}")

            tar.extractall(target_dir)


def main(argv=None):
    args = parse_args(argv)
    args.target_dir.mkdir(parents=True, exist_ok=True)

    client = _OCIPull(
        registry_url=_normalize_registry_url(args.registry_url),
        repository=args.repository.strip(),
        username=args.username.strip() if args.username else None,
        password=args.password.strip() if args.password else None,
        ssl_context=_ssl_context(args.insecure, args.ca_cert),
    )

    print(f"Pulling {args.repository}:{args.tag} from {args.registry_url} ...")

    with tempfile.TemporaryDirectory() as download_dir:
        client.download_files(args.tag, download_dir)

        archive = _find_archive(download_dir)
        print(f"Extracting {archive.name} -> {args.target_dir}")
        _safe_extract_archive(archive, args.target_dir)

        if args.keep_archive:
            copy2(archive, args.target_dir / archive.name)

    print(f"Offline installer ready in {args.target_dir}")


if __name__ == "__main__":
    main()
