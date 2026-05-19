from .models import ExtensionManifest
from .exceptions import ExtensionNotFoundException, ExtensionPullError
from pathlib import Path
import json
import shutil


class ociService:

    def __init__(self, repository_url: str, authentication) -> None:
        self.repository_url = repository_url
        self._authentication = authentication

        self.extension_dir = Path(
            f"{Path(__file__).parent.parent.parent}/mock_data"
        ).absolute()

    async def __aenter__(self):
        self._session = None
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._session = None
        return False

    async def connect(self) -> None:
        return True

    async def get_extensions_for_repository(self) -> set[str]:
        return set([str(tag.name) for tag in self.extension_dir.iterdir()])

    async def get_extension_manifests(
        self, tags: set[str] | None = None
    ) -> dict[str, ExtensionManifest]:
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
        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        with open(self.extension_dir / tag / "extension_manifest.json") as manifest:
            manifest_json = json.load(manifest)

        return ExtensionManifest(**manifest_json)

    async def pull_extension(self, tag: str) -> Path:
        existing_tags = await self.get_extensions_for_repository()
        if tag not in existing_tags:
            raise ExtensionNotFoundException(
                f"Extension with tag {tag} not found in {self.repository_url}"
            )

        source = Path(self.extension_dir / tag)
        dest = Path(__file__).parent.parent.parent / "tags"

        shutil.copytree(source, dest)

        return dest
