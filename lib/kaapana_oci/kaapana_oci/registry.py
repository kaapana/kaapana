import requests
import base64
import json
import re
import hashlib
import logging
import os
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, timezone
from pathlib import Path


class OCIRegistryDiscovery:
    def __init__(
        self,
        registry_url: str,
        repository: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.registry_url = registry_url.rstrip("/")
        self.repository = repository
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.bearer_token: Optional[str] = None
        self.basic_auth_header = self._build_basic_auth_header()

    def _build_basic_auth_header(self) -> Dict[str, str]:
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
        return (
            {"Authorization": f"Bearer {self.bearer_token}"}
            if self.bearer_token
            else self.basic_auth_header.copy()
        )

    def _request_with_auth_retry(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
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

    def _upload_blob(self, data: Union[str, bytes], media_type: str) -> Optional[str]:
        upload_url = f"{self.registry_url}/v2/{self.repository}/blobs/uploads/"
        try:
            resp = self._request_with_auth_retry(
                "POST", upload_url, headers={"Content-Type": "application/octet-stream"}
            )
            location = resp.headers["Location"]
            data_bytes = data.encode("utf-8") if isinstance(data, str) else data
            digest = f"sha256:{hashlib.sha256(data_bytes).hexdigest()}"
            upload_url = f"{location}&digest={digest}"

            self._request_with_auth_retry(
                "PUT", upload_url, headers={"Content-Type": media_type}, data=data_bytes
            )
            return digest
        except Exception as e:
            self.logger.error(f"Failed to upload blob: {e}")
            return None

    def _media_type_from_ext(self, ext: str) -> str:
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
        }.get(ext.lower(), "application/octet-stream")

    def _upload_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            data = Path(file_path).read_bytes()
            media_type = self._media_type_from_ext(Path(file_path).suffix)
            digest = self._upload_blob(data, media_type)
            if not digest:
                return None
            return {
                "digest": digest,
                "filename": Path(file_path).name,
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

    def _download_blob(self, digest: str) -> Optional[bytes]:
        try:
            url = f"{self.registry_url}/v2/{self.repository}/blobs/{digest}"
            resp = self._request_with_auth_retry("GET", url)
            return resp.content
        except Exception as e:
            self.logger.error(f"Failed to download blob {digest}: {e}")
            return None

    def get(self, tag: str) -> Dict[str, Any]:
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
        try:
            url = f"{self.registry_url}/v2/{self.repository}/tags/list"
            resp = self._request_with_auth_retry("GET", url)
            tags = resp.json().get("tags", None)
            if not tags:
                return []
            return tags
        except Exception as e:
            self.logger.error(f"Failed to list tags for {self.repository}: {e}")
            return []

    def get_all_metadata(
        self, specific_tag: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
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
                    with open(output_path, "wb") as f:
                        f.write(data)
                    self.logger.info(f"Downloaded: {output_path}")
                else:
                    self.logger.warning(f"Failed to download file: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Error downloading files for tag {tag}: {e}")
            return False
