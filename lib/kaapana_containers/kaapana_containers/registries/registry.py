import httpx
import base64
import http.cookiejar
import json
import re
import hashlib
import logging
from typing import AsyncIterator, Optional, List, Dict, Any, Union, Tuple, NewType
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

# Chunk size for hashing and streaming file blobs to the registry.
_FILE_CHUNK_SIZE = 1024 * 1024

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
        options: Dict[str, Any] = dict(self._client_options)
        # Never store or send cookies. Harbor sets a session cookie (sid) on every
        # response and enforces browser CSRF rules on any unsafe /v2/ request that
        # carries it, rejecting the request with "FORBIDDEN: CSRF token invalid".
        # Registry API clients authenticate per request via the Authorization
        # header and need no cookies (docker/oras never keep any either).
        options.setdefault("cookies", self._reject_all_cookies_jar())
        # Registries commonly redirect blob GETs (307) to object storage. httpx does
        # not follow redirects by default and a 307 is not an error, so without this
        # a blob download would silently return the empty redirect body.
        options.setdefault("follow_redirects", True)
        self._client = httpx.AsyncClient(**options)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _reject_all_cookies_jar() -> http.cookiejar.CookieJar:
        """Cookie jar that refuses to store any cookie (empty allowed-domains list)."""
        return http.cookiejar.CookieJar(
            policy=http.cookiejar.DefaultCookiePolicy(allowed_domains=[])
        )

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

    async def _request_with_auth_retry(
        self, method: str, url: str, content_factory=None, **kwargs
    ) -> httpx.Response:
        """Perform an HTTP request with automatic auth retry using OAuth 2.0 bearer tokens.

        Follows the OCI/Docker registry authentication flow:
        1. Makes initial request with configured credentials
        2. If 401 with WWW-Authenticate header, extracts realm/service/scope
        3. Requests bearer token from the auth server (realm URL)
        4. Retries original request with the bearer token

        This implements the OAuth 2.0 token-based authentication flow used by
        most OCI registries (Docker Hub, GitLab, Harbor, etc.).

        Args:
            content_factory: Zero-argument callable returning a fresh request body
                (e.g. a new bytes iterator). Use instead of ``content=`` for streamed
                bodies: a plain iterator would be consumed by the first attempt and
                could not be re-sent on the 401 retry.

        Raises:
            OCIError: On any non-2xx response.
        """
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        if content_factory is not None:
            kwargs["content"] = content_factory()
        response = await self._client.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401 and "WWW-Authenticate" in response.headers:
            token = await self._get_bearer_token(response.headers["WWW-Authenticate"])
            self.bearer_token = token
            headers["Authorization"] = f"Bearer {token}"
            if content_factory is not None:
                kwargs["content"] = content_factory()
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

    async def _start_blob_upload(self) -> str:
        """Initiate a blob upload session and return the absolute upload URL.

        POSTs to /v2/{repo}/blobs/uploads/; the registry responds with a Location
        header (possibly relative) pointing to the session the blob is PUT to.

        Raises:
            OCIError: If the registry does not return a Location header, or the POST fails.
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
        return location

    def _blob_commit_timeout(self, size: int) -> httpx.Timeout:
        """Request timeout for a blob-completion PUT, sized to the payload.

        The registry answers the PUT only after it has received, verified and
        committed the whole blob; behind a buffering proxy or slow storage that
        takes far longer than any fixed per-operation default (observed >60s for
        a ~1GB blob on Harbor, aborting the publish with ReadTimeout after the
        body was fully sent). Allow one second per MiB on top of the client's
        configured read timeout; an explicitly unlimited (None) read timeout is
        kept as is.
        """
        base = self._client.timeout
        if base.read is None:
            return base
        return httpx.Timeout(
            connect=base.connect,
            read=max(base.read, 60.0 + size / 2**20),
            write=base.write,
            pool=base.pool,
        )

    async def _complete_blob_upload(
        self,
        location: str,
        digest: SHA256Digest,
        media_type: str,
        size: Optional[int] = None,
        **kwargs,
    ) -> None:
        """PUT the blob content to the upload session URL with its digest.

        ``kwargs`` carry the body (``content=`` or ``content_factory=``) through to
        :meth:`_request_with_auth_retry`. Pass ``size`` for streamed bodies: the
        explicit Content-Length keeps httpx from falling back to chunked transfer
        encoding, which not every registry backend accepts for blob PUTs, and the
        read timeout is scaled to the payload (see :meth:`_blob_commit_timeout`).
        """
        headers = {"Content-Type": media_type}
        if size is not None:
            headers["Content-Length"] = str(size)
            kwargs.setdefault("timeout", self._blob_commit_timeout(size))
        separator = "&" if "?" in location else "?"
        await self._request_with_auth_retry(
            "PUT",
            f"{location}{separator}digest={digest}",
            headers=headers,
            **kwargs,
        )

    async def _blob_exists(self, digest: SHA256Digest) -> bool:
        """Whether the repository already holds the blob (HEAD, no body transfer).

        Errors count as "not there": the subsequent upload then surfaces the real
        problem with a meaningful message instead of this probe.
        """
        try:
            await self._request_with_auth_retry(
                "HEAD", f"{self.registry_url}/v2/{self.repository}/blobs/{digest}"
            )
            return True
        except OCIError:
            return False

    async def _upload_blob(self, data: Union[str, bytes], media_type: str) -> SHA256Digest:
        """Upload a small in-memory blob (config/metadata) to the OCI registry.

        The whole blob is uploaded in a single PUT and held in memory for the
        duration of the request. For file payloads use :meth:`_upload_file`, which
        streams from disk instead.

        Args:
            data: Raw bytes or string data to upload
            media_type: OCI media type (e.g., application/vnd.oci.image.config.v1+json)

        Returns:
            The SHA256 digest string of the uploaded blob.

        Raises:
            OCIError: If the registry does not return a Location header, or any HTTP step fails.
        """
        location = await self._start_blob_upload()
        data_bytes = data.encode("utf-8") if isinstance(data, str) else data
        digest = SHA256Digest(f"sha256:{hashlib.sha256(data_bytes).hexdigest()}")
        await self._complete_blob_upload(location, digest, media_type, content=data_bytes)
        return digest

    async def _upload_blob_from_file(
        self, file_path: Path, media_type: str
    ) -> Tuple[SHA256Digest, int]:
        """Upload a file as a blob, streaming it from disk in chunks.

        The file is read twice: once to compute the SHA256 digest the registry
        requires up front, then chunk-wise as the PUT request body. At no point is
        it held in memory as a whole, so multi-GB payloads (e.g. the offline
        installer tarball) upload with constant memory.

        Returns:
            Tuple of (SHA256 digest, file size in bytes).

        Raises:
            OSError: If the file cannot be read.
            OCIError: If any registry step fails.
        """
        sha256 = hashlib.sha256()
        size = 0
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(_FILE_CHUNK_SIZE), b""):
                sha256.update(chunk)
                size += len(chunk)
        digest = SHA256Digest(f"sha256:{sha256.hexdigest()}")

        # A blob already in the repository - e.g. from a retried publish whose
        # earlier attempt timed out client-side after the upload - is not sent again.
        if await self._blob_exists(digest):
            self.logger.info(f"Blob {digest} already in the registry, skipping upload")
            return digest, size

        def fresh_stream() -> AsyncIterator[bytes]:
            # Re-opens the file per request attempt so the 401 auth retry can
            # re-send the body. The blocking reads are acceptable: this client
            # runs one transfer at a time.
            async def stream() -> AsyncIterator[bytes]:
                with file_path.open("rb") as f:
                    while chunk := f.read(_FILE_CHUNK_SIZE):
                        yield chunk

            return stream()

        location = await self._start_blob_upload()
        await self._complete_blob_upload(
            location, digest, media_type, size=size, content_factory=fresh_stream
        )
        return digest, size

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

        Determines the media type from the file extension and streams the file
        from disk (see :meth:`_upload_blob_from_file`), so files larger than the
        available memory upload fine.

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
        path = Path(file_path)
        media_type = self._media_type_from_ext(path.suffix)
        digest, size = await self._upload_blob_from_file(path, media_type)
        name = stored_name if stored_name is not None else file_path
        return {"digest": digest, "filename": name, "mediaType": media_type, "size": size}

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
