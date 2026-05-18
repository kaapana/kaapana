import requests
import base64
import json
import re
import hashlib
import logging
import os
from typing import Optional, List, Dict, Any, Union, Tuple, NewType
from datetime import datetime, timezone
from pathlib import Path

SHA256Digest = NewType("SHA256Digest", str)
"""Type alias for SHA256 digest strings in format 'sha256:<hexdigest>'."""


class OCIRegistryDiscovery:
    """Low-level OCI registry client.

    Provides authentication, blob upload/download, manifest handling, and tag
    management following the OCI Distribution Specification (Docker Registry API
    v2). The class is deliberately lightweight - higher-level convenience logic
    lives in :class:`kaapana_extensions.extensions.ExtensionUtilityLibrary`.
    """
    def __init__(
        self,
        registry_url: str,
        repository: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize the OCIRegistryDiscovery client.

        Args:
            registry_url: Base URL of the OCI registry (e.g., 'https://registry.hzdr.de').
            repository: Repository name within the registry (e.g., 'user.name/kaapana/extensions').
            username: Optional username for basic authentication.
            password: Optional password for basic authentication.
        """
        self.logger = logging.getLogger(__name__)
        self.registry_url = registry_url.rstrip("/")
        self.repository = repository
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.bearer_token: Optional[str] = None
        self.basic_auth_header = self._build_basic_auth_header()

    def _build_basic_auth_header(self) -> Dict[str, str]:
        """Create HTTP Basic auth header if credentials are provided.

        Returns:
            Dict with 'Authorization' header if credentials provided, empty dict otherwise.
        """
        if self.username and self.password:
            auth = f"{self.username}:{self.password}".encode()
            token = base64.b64encode(auth).decode()
            return {"Authorization": f"Basic {token}"}
        return {}

    def _get_bearer_token(self, www_auth: str) -> Optional[str]:
        match = re.match(
            r'Bearer realm="([^"]+)",service="([^"]+)",scope="([^"]+)"', www_auth
        )
        if not match:
            self.logger.error(f"Failed to parse WWW-Authenticate header: {www_auth}")
            return None
        realm, service, scope = match.groups()
        try:
            resp = self.session.get(
                realm,
                params={"service": service, "scope": scope},
                auth=(
                    (self.username, self.password)
                    if self.username and self.password
                    else None
                ),
            )
            resp.raise_for_status()
            token = resp.json().get("token")
            self.logger.debug(f"Received bearer token: {token[:20]}...")
            return token
        except Exception as e:
            self.logger.error(f"Error getting bearer token: {e}")
            return None

    def _auth_headers(self) -> Dict[str, str]:
        """Return appropriate authorization headers for current auth state.

        Returns:
            Dict with Authorization header using either bearer token or basic auth.
        """
        return (
            {"Authorization": f"Bearer {self.bearer_token}"}
            if self.bearer_token
            else self.basic_auth_header.copy()
        )

    def _request_with_auth_retry(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """Perform an HTTP request with automatic auth retry using OAuth 2.0 bearer tokens.

        Follows the OCI/Docker registry authentication flow:
        1. Makes initial request with configured credentials
        2. If 401 with WWW-Authenticate header, extracts realm/service/scope
        3. Requests bearer token from the auth server (realm URL)
        4. Retries original request with the bearer token

        This implements the OAuth 2.0 token-based authentication flow used by
        most OCI registries (Docker Hub, GitLab, Harbor, etc.).
        """
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        response = self.session.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401 and "WWW-Authenticate" in response.headers:
            token = self._get_bearer_token(response.headers["WWW-Authenticate"])
            if token:
                self.bearer_token = token
                headers["Authorization"] = f"Bearer {token}"
                response = self.session.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def _upload_blob(self, data: Union[str, bytes], media_type: str) -> Optional[SHA256Digest]:
        """Upload raw blob data to the OCI registry.

        Follows the OCI blob upload API:
        1. POST to /v2/{repo}/blobs/uploads/ to initiate upload
        2. Registry responds with a Location header pointing to the upload URL
        3. PUT blob data to that URL with the digest query parameter
        4. Registry stores the blob and returns 201 Created

        Args:
            data: Raw bytes or string data to upload
            media_type: OCI media type (e.g., application/vnd.oci.image.config.v1+json)

        Returns:
            Optional[SHA256Digest]: The SHA256 digest string on success, or ``None`` on failure.

        Raises:
            ValueError: If the registry does not return a Location header during upload initiation.
        """
        upload_url = f"{self.registry_url}/v2/{self.repository}/blobs/uploads/"
        try:
            resp = self._request_with_auth_retry(
                "POST", upload_url, headers={"Content-Type": "application/octet-stream"}
            )
            location = resp.headers["Location"]
            data_bytes = data.encode("utf-8") if isinstance(data, str) else data
            digest = SHA256Digest(f"sha256:{hashlib.sha256(data_bytes).hexdigest()}")
            upload_url = f"{location}&digest={digest}"

            self._request_with_auth_retry(
                "PUT", upload_url, headers={"Content-Type": media_type}, data=data_bytes
            )
            return digest
        except Exception as e:
            self.logger.error(f"Failed to upload blob: {e}")
            return None

    def _media_type_from_ext(self, ext: str) -> str:
        """Map file extension to OCI media type.

        Args:
            ext: File extension (e.g., '.tar.gz', '.json')

        Returns:
            Corresponding OCI media type string.
            Defaults to 'application/octet-stream' for unknown types.
        """
        return {
            ".txt": "text/plain",
            ".json": "application/json",
            ".yaml": "application/x-yaml",
            ".yml": "application/x-yaml",
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".zip": "application/zip",
            ".tar": "application/x-tar",
            ".gz": "application/gzip",
            ".py": "text/x-python",
            ".js": "application/javascript",
            ".ts": "application/typescript",
            ".sh": "application/x-shellscript",
            ".sql": "text/sql",
            ".xml": "application/xml",
            ".csv": "text/csv",
            ".html": "text/html",
            ".css": "text/css",
        }.get(ext.lower(), "application/octet-stream")

    def _upload_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Upload a file as a blob and return its metadata.

        Reads the file content, determines the appropriate media type,
        uploads it as a blob, and returns metadata.

        Args:
            file_path: Path to the file to upload (relative or absolute)

        Returns:
            Dict with keys: digest, filename, mediaType, size
            Returns None if upload fails or file cannot be read.
        """
        try:
            data = Path(file_path).read_bytes()
            media_type = self._media_type_from_ext(Path(file_path).suffix)
            digest = self._upload_blob(data, media_type)
            if not digest:
                return None
            return {
                "digest": digest,
                "filename": file_path,
                "mediaType": media_type,
                "size": len(data),
            }
        except Exception as e:
            self.logger.error(f"Failed to upload file {file_path}: {e}")
            raise e

    def create_or_update_tag(
        self,
        tag: str,
        user_metadata: Dict[str, Any],
        files: Optional[List[str]] = None,
    ) -> bool:
        """Create or update a tag with the given metadata and layer descriptors.

        The config blob stores the unmodified extension manifest (user_metadata).
        The config blob stores mapping original filenames to their blob digests. (files)
        The manifest references the config and layer blobs.

        Args:
            tag: Tag name (e.g., 'myapp-1.0.0')
            user_metadata: Original extension manifest dict (unchanged).
            files: List of file paths to upload as layers.

        Returns:
            True if tag was successfully created/updated.

        Raises:
            RuntimeError: If registry operations fail.
        """
        try:
            metadata = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "repository": self.repository,
                "tag": tag,
                "user_metadata": user_metadata,
            }

            layers = []
            if files:
                metadata["files"] = []
                for f in files:
                    file_meta = self._upload_file(f)
                    if file_meta:
                        metadata["files"].append(
                            {
                                "filename": file_meta["filename"],
                                "digest": file_meta["digest"],
                            }
                        )
                        layers.append(
                            {k: file_meta[k] for k in ["digest", "mediaType", "size"]}
                        )

            config_json = json.dumps(metadata, indent=2)
            config_digest = self._upload_blob(
                config_json, "application/vnd.oci.image.config.v1+json"
            )
            if not config_digest:
                return False

            manifest = {
                "schemaVersion": 2,
                "config": {
                    "mediaType": "application/vnd.oci.image.config.v1+json",
                    "digest": config_digest,
                    "size": len(config_json.encode("utf-8")),
                },
                "layers": layers,
            }

            url = f"{self.registry_url}/v2/{self.repository}/manifests/{tag}"
            self._request_with_auth_retry(
                "PUT",
                url,
                headers={"Content-Type": "application/vnd.oci.image.manifest.v1+json"},
                json=manifest,
            )
            self.logger.info(
                f"Published tag {tag} with metadata and {len(layers)} layers"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to create/update tag {tag}: {e}")
            return False

    def _download_blob(self, digest: SHA256Digest) -> Optional[bytes]:
        """Download a blob by its digest.

        Args:
            digest: Blob digest in 'sha256:<hexdigest>' format

        Returns:
            Raw bytes of the downloaded blob

        Raises:
            requests.HTTPError: If blob not found or other HTTP error
        """
        try:
            url = f"{self.registry_url}/v2/{self.repository}/blobs/{digest}"
            resp = self._request_with_auth_retry("GET", url)
            return resp.content
        except Exception as e:
            self.logger.error(f"Failed to download blob {digest}: {e}")
            return None

    def get(self, tag: str) -> Dict[str, Any]:
        """Get metadata for a tag.

        Fetches the manifest for the given tag, downloads the config blob,
        and returns the decoded metadata.

        Args:
            tag: Tag name to look up

        Returns:
            The user metadata stored in the config blob.
        """
        manifest_url = f"{self.registry_url}/v2/{self.repository}/manifests/{tag}"
        headers = {"Accept": "application/vnd.oci.image.manifest.v1+json"}
        manifest_resp = self._request_with_auth_retry(
            "GET", manifest_url, headers=headers
        )
        manifest = manifest_resp.json()

        config_digest = manifest["config"]["digest"]
        config_url = f"{self.registry_url}/v2/{self.repository}/blobs/{config_digest}"
        config_resp = self._request_with_auth_retry("GET", config_url)
        metadata = config_resp.json()
        return metadata

    def list_tags(self) -> List[str]:
        """List all tags in the repository.

        Returns:
            List of tag names. Empty list if no tags exist, response is empty, or the request is unauthorized (e.g., repository not yet created).
        """
        try:
            url = f"{self.registry_url}/v2/{self.repository}/tags/list"
            resp = self._request_with_auth_retry("GET", url)
            tags = resp.json().get("tags", None)
            if not tags:
                return []
            return tags
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                # OCI Distribution Spec: NAME_UNKNOWN means the repository has not been
                # created yet — a valid state before the first push.
                # https://github.com/opencontainers/distribution-spec/blob/main/spec.md#error-codes
                try:
                    errors = e.response.json().get("errors", [])
                    is_name_unknown = any(
                        err.get("code") == "NAME_UNKNOWN" for err in errors
                    )
                except Exception:
                    is_name_unknown = False
                if is_name_unknown:
                    self.logger.debug(f"Repository {self.repository} does not exist yet")
                    return []
            self.logger.error(f"Failed to list tags for {self.repository}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to list tags for {self.repository}: {e}")
            return []

    def get_all_metadata(
        self, specific_tag: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Get metadata for all tags or a specific tag.

        Args:
            specific_tag: If provided, only returns metadata for this tag.
                         If None, returns metadata for all tags.

        Returns:
            List of (tag, metadata) tuples. Empty list if no tags found.
        """
        tags = [specific_tag] if specific_tag else self.list_tags()
        if not tags:
            return []

        all_metadata = []
        for tag in tags:
            meta = self.get(tag)
            if meta:
                all_metadata.append((tag, meta))
        return all_metadata

    def delete_tag(self, tag: str) -> bool:
        """Delete only the manifest for a tag.
        The manifest reference is removed; config and layer blobs are left in the
        registry. Unreferenced blobs will be cleaned up by the registry's garbage
        collector (if configured).
        """
        try:
            manifest_url = f"{self.registry_url}/v2/{self.repository}/manifests/{tag}"
            headers = {"Accept": "application/vnd.oci.image.manifest.v1+json"}
            manifest_resp = self._request_with_auth_retry(
                "GET", manifest_url, headers=headers
            )
            digest = manifest_resp.headers.get("Docker-Content-Digest")

            if not digest:
                self.logger.error(f"Digest not found for tag {tag}")
                return False

            delete_url = f"{self.registry_url}/v2/{self.repository}/manifests/{digest}"
            self._request_with_auth_retry("DELETE", delete_url)
            self.logger.info(f"Deleted tag {tag}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete tag {tag}: {e}")
            return False

    def download_files(self, tag: str, output_dir: str = ".") -> bool:
        """Download all files associated with a tag to the specified directory.

        Fetches the tag's metadata, downloads each referenced file as a blob,
        and writes them to the output directory with their original filenames.

        Args:
            tag: Tag name to download files from
            output_dir: Directory to write files to (default: current directory)

        Returns:
            True if download completed (even if no files were present)

        Raises:
            RuntimeError: If no metadata found for tag
        """
        try:
            metadata_list = self.get_all_metadata(tag)
            if not metadata_list:
                self.logger.error(f"No metadata found for tag {tag}")
                return False

            _, metadata = metadata_list[0]
            if "files" not in metadata:
                self.logger.info(f"No files associated with tag {tag}")
                return True

            os.makedirs(output_dir, exist_ok=True)

            for file_info in metadata["files"]:
                filename = file_info["filename"]
                digest = file_info["digest"]
                data = self._download_blob(digest)
                if data:
                    output_path = os.path.join(output_dir, filename)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(data)
                    self.logger.info(f"Downloaded: {output_path}")
                else:
                    self.logger.warning(f"Failed to download file: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Error downloading files for tag {tag}: {e}")
            return False
