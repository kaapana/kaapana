import httpx
import base64
import json
import re
import hashlib
import logging
from typing import Optional, List, Dict, Any, Union, Tuple, NewType
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

SHA256Digest = NewType("SHA256Digest", str)
"""Type alias for SHA256 digest strings in format 'sha256:<hexdigest>'."""


class OCIError(Exception):
    """OCI registry error with the error code from the OCI Distribution Spec.

    Spec reference: https://github.com/opencontainers/distribution-spec/blob/main/spec.md#error-codes

    Common codes and their meaning:

    ==================== ================================================================
    Code                 Meaning
    ==================== ================================================================
    BLOB_UNKNOWN         Blob unknown to registry (digest not found).
    BLOB_UPLOAD_INVALID  Blob upload session is invalid or already completed.
    BLOB_UPLOAD_UNKNOWN  Blob upload session not found.
    DIGEST_INVALID       Digest does not match uploaded content.
    MANIFEST_BLOB_UNKNOWN A blob referenced by the manifest is not found.
    MANIFEST_INVALID     Manifest content is malformed or violates spec constraints.
    MANIFEST_UNKNOWN     Manifest (tag or digest) not found in this repository.
    MANIFEST_UNVERIFIED  Manifest signature cannot be verified.
    NAME_INVALID         Repository name is syntactically invalid.
    NAME_UNKNOWN         Repository does not exist in this registry.
    SIZE_INVALID         Provided layer size does not match uploaded content.
    TAG_INVALID          Tag name is syntactically invalid.
    UNAUTHORIZED         Authentication required or credentials invalid (WWW-Authenticate).
    DENIED               Access denied; credentials valid but not authorized.
    UNSUPPORTED          Operation not supported by this registry.
    ==================== ================================================================

    Attributes:
        code: OCI error code (e.g. ``"MANIFEST_UNKNOWN"``), or ``None`` when
              the registry did not return a structured error body.
    """

    def __init__(self, message: str, code: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:
        msg = super().__str__()
        return f"{self.code}: {msg}" if self.code else msg

    @classmethod
    def from_response(cls, response: httpx.Response) -> "OCIError":
        code: Optional[str] = None
        message = f"HTTP {response.status_code}"
        try:
            errors = response.json().get("errors", [])
            if errors:
                code = errors[0].get("code")
                message = errors[0].get("message", message)
                detail = errors[0].get("detail")
                if detail:
                    message = f"{message}: {detail}"
        except (json.JSONDecodeError, AttributeError):
            text = response.text[:200]
            if text:
                message = f"{message}: {text}"
        return cls(message, code=code)


class OCIRegistryDiscovery:
    """Low-level OCI registry client.

    Provides authentication, blob upload/download, manifest handling, and tag
    management following the OCI Distribution Specification (Docker Registry API
    v2). The class is deliberately lightweight - higher-level convenience logic
    lives in :class:`kaapana_extensions.extensions.ExtensionUtilityLibrary`.

    Must be used as an async context manager::

        async with OCIRegistryDiscovery(...) as client:
            tags = await client.list_tags()
    """

    def __init__(
        self,
        registry_url: str,
        repository: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the OCIRegistryDiscovery client.

        Args:
            registry_url: Base URL of the OCI registry (e.g., 'https://registry.hzdr.de').
            repository: Repository name within the registry (e.g., 'user.name/kaapana/extensions').
            username: Optional username for basic authentication.
            password: Optional password for basic authentication.
            client_options: Options forwarded to :class:`httpx.AsyncClient`
                (e.g. ``{"timeout": 60.0, "verify": False}``).
        """
        self.logger = logging.getLogger(__name__)
        self.registry_url = registry_url.rstrip("/")
        self.repository = repository
        self.username = username
        self.password = password
        self.bearer_token: Optional[str] = None
        self.basic_auth_header = self._build_basic_auth_header()
        self._client: Optional[httpx.AsyncClient] = None
        self._client_options: Dict[str, Any] = client_options or {}

    async def __aenter__(self) -> "OCIRegistryDiscovery":
        self._client = httpx.AsyncClient(**self._client_options)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_basic_auth_header(self) -> Dict[str, str]:
        """Create HTTP Basic auth header if credentials are provided.

        Returns:
            Dict with 'Authorization' header if credentials provided, empty dict otherwise.
        """
        if self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            return {"Authorization": f"Basic {token}"}
        return {}

    async def _get_bearer_token(self, www_auth: str) -> str:
        match = re.match(
            r'Bearer realm="([^"]+)",service="([^"]+)"(?:,scope="([^"]+)")?', www_auth
        )
        if not match:
            raise OCIError(
                f"cannot parse WWW-Authenticate header: {www_auth!r}",
                code="UNAUTHORIZED",
            )
        realm, service, scope = match.groups()
        params: Dict[str, str] = {"service": service}
        if scope:
            params["scope"] = scope

        auth = (self.username, self.password) if self.username and self.password else None
        resp = await self._client.get(realm, params=params, auth=auth)
        if resp.is_error:
            raise OCIError(
                f"token endpoint returned HTTP {resp.status_code}",
                code="UNAUTHORIZED",
            )
        token = resp.json().get("token")
        if not token:
            raise OCIError("token endpoint did not return a token", code="UNAUTHORIZED")
        self.logger.debug(f"Received bearer token: {token[:20]}...")
        return token

    def _auth_headers(self) -> Dict[str, str]:
        """Return appropriate authorization headers for current auth state.

        Returns:
            Dict with Authorization header using either bearer token or basic auth.
        """
        if self.bearer_token:
            return {"Authorization": f"Bearer {self.bearer_token}"}
        return self.basic_auth_header.copy()

    async def _request_with_auth_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Perform an HTTP request with automatic auth retry using OAuth 2.0 bearer tokens.

        Follows the OCI/Docker registry authentication flow:
        1. Makes initial request with configured credentials
        2. If 401 with WWW-Authenticate header, extracts realm/service/scope
        3. Requests bearer token from the auth server (realm URL)
        4. Retries original request with the bearer token

        This implements the OAuth 2.0 token-based authentication flow used by
        most OCI registries (Docker Hub, GitLab, Harbor, etc.).

        Raises:
            OCIError: On any non-2xx response.
        """
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        response = await self._client.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401 and "WWW-Authenticate" in response.headers:
            token = await self._get_bearer_token(response.headers["WWW-Authenticate"])
            self.bearer_token = token
            headers["Authorization"] = f"Bearer {token}"
            response = await self._client.request(method, url, headers=headers, **kwargs)

        if response.is_error:
            raise OCIError.from_response(response)
        return response

    async def check_login(self) -> bool:
        """Verify that the current credentials are accepted by the registry.

        Returns:
            ``True`` on success.

        Raises:
            OCIError: If the credentials are rejected (``UNAUTHORIZED`` /
                      ``DENIED``) or the registry is unreachable.
        """
        await self._request_with_auth_retry("GET", f"{self.registry_url}/v2/")
        return True

    async def _upload_blob(self, data: Union[str, bytes], media_type: str) -> SHA256Digest:
        """Upload raw blob data to the OCI registry.

        Follows the OCI blob upload API:
        1. POST to /v2/{repo}/blobs/uploads/ to initiate upload
        2. Registry responds with a Location header pointing to the upload URL
        3. PUT blob data to that URL with the digest query parameter
        4. Registry stores the blob and returns 201 Created

        The whole blob is uploaded in a single PUT, so ``data`` is held in
        memory for the duration of the request. Blobs larger than the available memory
        cannot be uploaded and will fail with a memory error.

        Args:
            data: Raw bytes or string data to upload
            media_type: OCI media type (e.g., application/vnd.oci.image.config.v1+json)

        Returns:
            The SHA256 digest string of the uploaded blob.

        Raises:
            OCIError: If the registry does not return a Location header, or any HTTP step fails.
        """
        resp = await self._request_with_auth_retry(
            "POST",
            f"{self.registry_url}/v2/{self.repository}/blobs/uploads/",
            headers={"Content-Type": "application/octet-stream"},
        )
        location = resp.headers.get("Location")
        if not location:
            raise OCIError("registry did not return a Location header", code="BLOB_UPLOAD_INVALID")

        if not location.startswith(("http://", "https://")):
            location = urljoin(self.registry_url.rstrip("/") + "/", location.lstrip("/"))

        data_bytes = data.encode("utf-8") if isinstance(data, str) else data
        digest = SHA256Digest(f"sha256:{hashlib.sha256(data_bytes).hexdigest()}")

        separator = "&" if "?" in location else "?"
        await self._request_with_auth_retry(
            "PUT",
            f"{location}{separator}digest={digest}",
            headers={"Content-Type": media_type},
            content=data_bytes,
        )
        return digest

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

    async def _upload_file(self, file_path: str, stored_name: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file as a blob and return its metadata.

        Reads the file content, determines the appropriate media type,
        uploads it as a blob, and returns metadata.

        The file is held fully in memory before being uploaded (see
        :meth:`_upload_blob`); the host needs free RAM of at least the size of the file.

        Args:
            file_path: Absolute (or cwd-relative) path to the file to read.
            stored_name: The filename to record in the registry metadata.
                         Defaults to ``file_path`` when not provided.

        Returns:
            Dict with keys: digest, filename, mediaType, size

        Raises:
            OSError: If the file cannot be read.
            OCIError: If the blob upload fails.
        """
        data = Path(file_path).read_bytes()
        media_type = self._media_type_from_ext(Path(file_path).suffix)
        digest = await self._upload_blob(data, media_type)
        name = stored_name if stored_name is not None else file_path
        return {"digest": digest, "filename": name, "mediaType": media_type, "size": len(data)}

    async def create_or_update_tag(
        self,
        tag: str,
        user_metadata: Dict[str, Any],
        files: Optional[List[str]] = None,
        base_dir: Optional[str] = None,
    ) -> bool:
        """Create or update a tag with the given metadata and layer descriptors.

        The config blob stores the unmodified extension manifest (user_metadata).
        The config blob stores mapping original filenames to their blob digests. (files)
        The manifest references the config and layer blobs.

        Args:
            tag: Tag name (e.g., 'myapp-1.0.0')
            user_metadata: Original extension manifest dict (unchanged).
            files: List of relative file paths to upload as layers.
            base_dir: If provided, file paths in ``files`` are resolved relative
                      to this directory. Avoids the need for ``os.chdir``.

        Returns:
            True if tag was successfully created/updated.

        Raises:
            OCIError: If any registry operation fails.
            OSError: If a file in ``files`` cannot be read.
        """
        metadata: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "repository": self.repository,
            "tag": tag,
            "user_metadata": user_metadata,
        }

        layers = []
        if files:
            metadata["files"] = []
            for f in files:
                abs_path = str(Path(base_dir) / f) if base_dir else f
                file_meta = await self._upload_file(abs_path, stored_name=f)
                metadata["files"].append({"filename": file_meta["filename"], "digest": file_meta["digest"]})
                layers.append({k: file_meta[k] for k in ["digest", "mediaType", "size"]})

        config_json = json.dumps(metadata, indent=2)
        config_digest = await self._upload_blob(config_json, "application/vnd.oci.image.config.v1+json")

        manifest = {
            "schemaVersion": 2,
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": config_digest,
                "size": len(config_json.encode("utf-8")),
            },
            "layers": layers,
        }

        await self._request_with_auth_retry(
            "PUT",
            f"{self.registry_url}/v2/{self.repository}/manifests/{tag}",
            headers={"Content-Type": "application/vnd.oci.image.manifest.v1+json"},
            content=json.dumps(manifest).encode("utf-8"),
        )
        self.logger.info(f"Published tag {tag} with metadata and {len(layers)} layers")
        return True

    async def _download_blob(self, digest: SHA256Digest) -> bytes:
        """Download a blob by its digest.

        The response body is buffered completely in memory (``resp.content``), so a
        blob larger than the available memory will fail with a memory error.

        Args:
            digest: Blob digest in 'sha256:<hexdigest>' format

        Returns:
            Raw bytes of the downloaded blob.

        Raises:
            OCIError: If blob not found or other HTTP error.
        """
        resp = await self._request_with_auth_retry(
            "GET", f"{self.registry_url}/v2/{self.repository}/blobs/{digest}"
        )
        return resp.content

    async def get(self, tag: str) -> Dict[str, Any]:
        """Get metadata for a tag.

        Fetches the manifest for the given tag, downloads the config blob,
        and returns the decoded metadata.

        Args:
            tag: Tag name to look up

        Returns:
            The user metadata stored in the config blob.

        Raises:
            OCIError: If the tag does not exist, any HTTP error occurs, or the
                      manifest/config body cannot be parsed.
        """
        manifest_resp = await self._request_with_auth_retry(
            "GET",
            f"{self.registry_url}/v2/{self.repository}/manifests/{tag}",
            headers={"Accept": "application/vnd.oci.image.manifest.v1+json"},
        )
        try:
            config_digest = manifest_resp.json()["config"]["digest"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise OCIError(f"cannot parse manifest for {tag!r}: {exc}", code="MANIFEST_INVALID") from exc

        config_resp = await self._request_with_auth_retry(
            "GET", f"{self.registry_url}/v2/{self.repository}/blobs/{config_digest}"
        )
        try:
            return config_resp.json()
        except json.JSONDecodeError as exc:
            raise OCIError(f"config blob for {tag!r} is not valid JSON: {exc}", code="MANIFEST_INVALID") from exc

    async def list_tags(self) -> List[str]:
        """List all tags in the repository.

        Returns:
            List of tag names. Empty list if the repository exists but has no tags.

        Raises:
            OCIError: On any registry error, including ``NAME_UNKNOWN`` when the
                      repository does not exist yet. Callers that treat an absent
                      repository as an empty list should catch
                      ``OCIError`` with ``code == "NAME_UNKNOWN"``.
        """
        resp = await self._request_with_auth_retry(
            "GET", f"{self.registry_url}/v2/{self.repository}/tags/list"
        )
        return resp.json().get("tags") or []

    async def get_all_metadata(
        self, specific_tag: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Get metadata for all tags or a specific tag.

        Args:
            specific_tag: If provided, only returns metadata for this tag.
                         If None, returns metadata for all tags.

        Returns:
            List of (tag, metadata) tuples. Empty list if no tags found.

        Raises:
            OCIError: If any tag's metadata cannot be fetched.
        """
        tags = [specific_tag] if specific_tag else await self.list_tags()
        return [(tag, await self.get(tag)) for tag in tags]

    async def delete_tag(self, tag: str) -> bool:
        """Delete only the manifest for a tag.

        The manifest reference is removed; config and layer blobs are left in the
        registry. Unreferenced blobs will be cleaned up by the registry's garbage
        collector (if configured).

        Computes the digest from the manifest body rather than relying on the
        Docker-specific Docker-Content-Digest header.

        Raises:
            OCIError: If the tag does not exist or the delete request fails.
        """
        manifest_resp = await self._request_with_auth_retry(
            "GET",
            f"{self.registry_url}/v2/{self.repository}/manifests/{tag}",
            headers={"Accept": "application/vnd.oci.image.manifest.v1+json"},
        )
        digest = f"sha256:{hashlib.sha256(manifest_resp.content).hexdigest()}"
        await self._request_with_auth_retry(
            "DELETE", f"{self.registry_url}/v2/{self.repository}/manifests/{digest}"
        )
        self.logger.info(f"Deleted tag {tag}")
        return True

    async def download_files(self, tag: str, output_dir: str = ".") -> bool:
        """Download all files associated with a tag to the specified directory.

        Fetches the tag's metadata, downloads each referenced file as a blob,
        and writes them to the output directory with their original filenames.

        Each file is held fully in memory before being written (see
        :meth:`_download_blob`); the host needs free RAM of at least the size of the
        largest file.

        Args:
            tag: Tag name to download files from
            output_dir: Directory to write files to (default: current directory)

        Returns:
            True if download completed (even if no files were present).

        Raises:
            OCIError: If the tag is unknown or any blob download fails.
            ValueError: If a filename in the registry metadata would escape output_dir.
        """
        metadata_list = await self.get_all_metadata(tag)
        if not metadata_list:
            raise OCIError(f"no metadata found for tag {tag!r}", code="MANIFEST_UNKNOWN")

        _, metadata = metadata_list[0]
        if "files" not in metadata:
            self.logger.info(f"No files associated with tag {tag}")
            return True

        safe_root = Path(output_dir).resolve()
        safe_root.mkdir(parents=True, exist_ok=True)

        for file_info in metadata["files"]:
            filename = file_info["filename"]
            dest = (safe_root / filename).resolve()
            if not dest.is_relative_to(safe_root):
                raise ValueError(
                    f"filename {filename!r} in registry metadata would escape the output directory"
                )
            data = await self._download_blob(file_info["digest"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            self.logger.info(f"Downloaded: {dest}")

        return True
