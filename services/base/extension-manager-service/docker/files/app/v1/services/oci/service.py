from .models import ExtensionManifest
from .exceptions import ExtensionNotFoundException, ExtensionPullError
from pathlib import Path
import json


class ociService:

    def __init__(self, repository_url: str, authentication) -> None:
        """
        Initializes the ociService instance.
        In a real implementation, this constructor could be used to set up any necessary connections to the OCI registry or to perform any necessary setup before the service can be used.
        """

        self.repository_url = repository_url
        self._authentication = authentication

        self.extension_dir = Path(f"/app/v1/mock_data")

    async def __aenter__(self):
        """Enter async context – establish mock connection."""
        # Placeholder for real async session setup (e.g., aiohttp.ClientSession)
        self._session = None
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context – cleanup mock connection."""
        self._session = None
        return False

    async def connect(self) -> None:
        """
        Makes a head request to the registry to check if the repository exists and the authentication is valid.
        If the request is successful, it returns None.
        If the request fails, it raises an exception.

        :param registry: TODO
        :param repository: TODO
        :param reference: TODO
        :param authentication: TODO
        """

        pass

    async def get_extensions_for_repository(self) -> set[str]:
        """
        Fetches the list of extensions available in the given repository.
        This is a placeholder implementation that returns a static list of extensions.
        In a real implementation, this method would query the OCI registry for the given repository and return the list of extensions available there.

        :rtype: list[Extension]
        """

        return set([str(tag.name) for tag in self.extension_dir.iterdir()])

    async def get_extension_manifests(
        self, tags: set[str] | None = None
    ) -> list[ExtensionManifest]:
        """
        Fetches the manifests of the extensions in the given repository.
        This is a placeholder implementation that returns static manifests.
        In a real implementation, this method would query the OCI registry for the given repository and return the manifests of the extensions available there.

        :param tags: TODO
        :return: TODO
        :rtype: list[ExtensionManifest]
        """
        manifests = []
        existing_tags = await self.get_extensions_for_repository()
        if tags:
            filtered_tags = existing_tags.intersection(tags)

            for tag in filtered_tags:
                manifest = await self.get_extension_manifest(tag)
                manifests.append(manifest)
        else:
            for tag in existing_tags:
                manifest = await self.get_extension_manifest(tag)
                manifests.append(manifest)

        return manifests

    async def get_extension_manifest(self, tag: str) -> ExtensionManifest:
        """
        Fetches the manifest of a specific extension in the given repository.
        This is a placeholder implementation that returns a static manifest.
        In a real implementation, this method would query the OCI registry for the given repository and return the manifest of the specified extension.

        :param tag: TODO
        :return: TODO
        :rtype: ExtensionManifest
        """
        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        with open(self.extension_dir / tag / "manifest.json") as manifest:
            manifest_json = json.load(manifest)

        return ExtensionManifest(**manifest_json)

    async def pull_extension(self, tag: str) -> Path:
        """
        Pulls a specific extension from the given repository.
        This is a placeholder implementation that does nothing.
        In a real implementation, this method would query the OCI registry for the given repository and pull the specified extension.

        :param tag: TODO
        :raises ExtensionPullError: TODO
        """

        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        return Path(f"/app/v1/mock_data/{tag}")
