import base64
import json
import os
from pathlib import Path
from urllib import parse

from kaapana_extensions.extensions import ExtensionUtilityLibrary
from v1.services.encryption import decrypt

from .exceptions import ExtensionNotFoundException, ExtensionPullError
from .models import ExtensionManifest


class ociService:

    def __init__(self, repository_url: str, authentication: str) -> None:
        """
        Initializes the ociService instance.

        :param repository_url:
        :param authentication: base64 encoded json string {"username": <>, "password": <>}
        """

        self.repository_url = repository_url
        self._authentication = authentication

        parsed_url = parse.urlparse(self.repository_url)

        self.extensions_download_dir = Path(f"/extensions/{parsed_url.hostname}")
        os.makedirs(name=self.extensions_download_dir, exist_ok=True)

        auth = decrypt(authentication)

        self.extension_lib = ExtensionUtilityLibrary(
            registry=parsed_url.scheme + "://" + parsed_url.netloc,
            repo=parsed_url.path.lstrip("/"),
            username=auth["username"],
            password=auth["password"],
        )
        self.extension_lib.check_login()

    async def __aenter__(self):
        """Enter async context – establish mock connection."""
        # Placeholder for real async session setup (e.g., aiohttp.ClientSession)
        self._session = None
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context – cleanup mock connection."""
        self._session = None
        return False

    async def connect(self) -> bool:
        """
        Makes a head request to the registry to check if the repository exists and the authentication is valid.
        If the request is successful, it returns True.
        If the request fails, it returns False.
        """

        return self.extension_lib.check_login()

    async def get_extensions_for_repository(self) -> set[str]:
        """
        Fetches the list of extensions available in the given repository.
        This is a placeholder implementation that returns a static list of extensions.
        In a real implementation, this method would query the OCI registry for the given repository and return the list of extensions available there.

        :rtype: list[str]
        """

        return set(self.extension_lib.list_tags())

    async def get_extension_manifests(
        self, tags: set[str] | None = None
    ) -> dict[str, ExtensionManifest]:
        """
        Fetches the manifests of the extensions in the given repository.
        This is a placeholder implementation that returns static manifests.
        In a real implementation, this method would query the OCI registry for the given repository and return the manifests of the extensions available there.

        :param tags: Set of extension tags
        :return: Dictionary with tag as key and the extension manifest as value
        :rtype: dict[str, ExtensionManifest]
        """
        manifests = {}
        existing_tags = await self.get_extensions_for_repository()
        if tags:
            filtered_tags = existing_tags.intersection(tags)

            for tag in filtered_tags:
                manifest = await self.get_extension_manifest(tag)
                manifests[tag] = manifest
        else:
            for tag in existing_tags:
                manifest = await self.get_extension_manifest(tag)
                manifests[tag] = manifest

        return manifests

    async def get_extension_manifest(self, tag: str) -> ExtensionManifest:
        """
        Fetches the manifest of a specific extension in the given repository.
        This is a placeholder implementation that returns a static manifest.
        In a real implementation, this method would query the OCI registry for the given repository and return the manifest of the specified extension.

        :param tag: Tag of an extensions
        :return: Return the extension manifest for the extension tag
        :rtype: ExtensionManifest
        """
        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        return ExtensionManifest(**self.extension_lib.get_extension(tag))

    async def pull_extension(self, tag: str) -> Path:
        """
        Pulls a specific extension from the given repository.
        This is a placeholder implementation that does nothing.
        In a real implementation, this method would query the OCI registry for the given repository and pull the specified extension.

        :param tag: Tag of an extension
        :return: The path, where the extension was downloaded to.
        :rtype: Path
        :raises ExtensionNotFoundException: If the tag is not installed it raises ExtensionNotFoundException.
        """

        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        archive_path = self.extension_lib.pull(
            tag=tag, output_dir=self.extensions_download_dir / tag
        )
        return Path(str(archive_path).rstrip(".tar.gz"))
