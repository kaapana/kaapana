import json
import os
from pathlib import Path
from urllib import parse

from kaapana_containers.registries.registry import OCIError
from kaapana_extensions.extensions import ExtensionUtilityLibrary
from v1.services.encryption import decrypt
from v1.services.logger import get_logger

from .exceptions import ExtensionNotFoundException
from .models import ExtensionManifest

logger = get_logger(__name__)


class ociService:

    def __init__(self, repository_url: str, authentication: str) -> None:
        """
        Initializes the ociService instance.

        :param repository_url:
        :param authentication: Fernet-encrypted JSON string {"username": <>, "password": <>}
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

    async def __aenter__(self) -> "ociService":
        """Enter async context — opens the HTTP client and verifies credentials.

        Raises:
            OCIError: If the registry rejects the credentials (``UNAUTHORIZED`` /
                      ``DENIED``) or is unreachable.
        """
        await self.extension_lib.__aenter__()
        try:
            await self.extension_lib.check_login()
        except BaseException as e:
            await self.extension_lib.__aexit__(type(e), e, e.__traceback__)
            logger.error(f"Registry login failed for {self.repository_url}: {e}")
            raise
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        """Exit async context — closes the HTTP client."""
        await self.extension_lib.__aexit__(exc_type, exc, tb)
        return False

    async def get_extensions_for_repository(self) -> set[str]:
        """
        Fetches the list of extensions available in the given repository.

        :rtype: set[str]
        :raises OCIError: On any registry error except NAME_UNKNOWN (empty repository
                          returns an empty set).
        """
        try:
            return set(await self.extension_lib.list_tags())
        except OCIError as e:
            if e.code == "NAME_UNKNOWN":
                return set()
            raise

    async def get_extension_manifests(
        self, tags: set[str] | None = None
    ) -> dict[str, ExtensionManifest]:
        """
        Fetches the manifests of the extensions in the given repository.

        :param tags: Set of extension tags
        :return: Dictionary with tag as key and the extension manifest as value
        :rtype: dict[str, ExtensionManifest]
        """
        existing_tags = await self.get_extensions_for_repository()
        target_tags = existing_tags.intersection(tags) if tags else existing_tags
        return {
            tag: ExtensionManifest(**await self.extension_lib.get_extension(tag))
            for tag in target_tags
        }

    async def get_extension_manifest(self, tag: str) -> ExtensionManifest:
        """
        Fetches the manifest of a specific extension in the given repository.

        :param tag: Tag of an extensions
        :return: Return the extension manifest for the extension tag
        :rtype: ExtensionManifest
        """
        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        return ExtensionManifest(**await self.extension_lib.get_extension(tag))

    async def pull_extension(self, tag: str) -> Path:
        """
        Pulls a specific extension from the given repository.

        :param tag: Tag of an extension
        :return: The path where the extension was downloaded to.
        :rtype: Path
        :raises ExtensionNotFoundException: If the tag is not found in the repository.
        :raises OCIError: If the registry pull fails.
        """

        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        return await self.extension_lib.pull(
            tag=tag, output_dir=self.extensions_download_dir / tag
        )
