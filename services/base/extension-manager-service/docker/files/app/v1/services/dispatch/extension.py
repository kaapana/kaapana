from pathlib import Path
from .content import Content, ContentInstaller
import json


class Extension:
    def __init__(
        self,
        extension_path: Path,
    ):
        with open(extension_path / "manifest.json") as f:
            extension_manifest = json.load(f)
        contents = []

        for content in extension_manifest.get("contents", []):
            contents.append(
                Content(
                    name=content["name"],
                    content_type=content["contentType"],
                    path=extension_path / content["name"],
                )
            )
        self.contents: list[Content] = contents


class ExtensionInstaller:
    def __init__(self, installers: list[ContentInstaller]):
        self.installers = installers

    async def install_content(self, content: Content):
        content_installer = self._find_installer(content)
        return await content_installer.install(content)

    def _find_installer(self, content: Content) -> ContentInstaller | None:
        for installer in self.installers:
            if installer.can_install(content):
                return installer
        raise Exception(f"No installer found for content type {content.content_type}")
