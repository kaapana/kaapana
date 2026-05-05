from pathlib import Path
from .content import Content, ContentInstaller, ContentDiscovery
import json


class Extension:
    def __init__(self, contents: list[Content]):
        self.contents = contents


class ExtensionInstaller:
    def __init__(self, installers: list[ContentInstaller]):
        self.installers = installers

    async def install(self, extension: Extension):
        for content in extension.contents:
            installer = self._find_installer(content)
            await installer.install(content)

    def _find_installer(self, content: Content) -> ContentInstaller | None:
        for installer in self.installers:
            if installer.can_install(content):
                return installer
        raise Exception(f"No installer found for content type {content.content_type}")


class ExtensionDiscovery:
    def __init__(self, content_discoveries: list[ContentDiscovery]):
        self.content_discoveries = content_discoveries

    def discover(self, extension_path: Path) -> Extension:
        with open(extension_path / "manifest.json") as f:
            extension_manifest = json.load(f)
        contents = []

        for content in extension_manifest.get("contents", []):
            detector = self._find_detector(extension_path / content["path"])
            if detector is not None:
                created_content = detector.create(extension_path / content["path"])
                contents.append(created_content)
        return Extension(contents=contents)

    def _find_detector(self, path: Path) -> ContentDiscovery | None:
        for detector in self.content_discoveries:
            if detector.matches(path):
                return detector
        return None
