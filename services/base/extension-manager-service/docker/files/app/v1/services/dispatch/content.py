from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass


@dataclass
class InstallationResult:
    success: bool
    message: str | None = None


class ContentInstaller(ABC):
    @abstractmethod
    def can_install(self, content) -> bool:
        pass

    @abstractmethod
    async def install(self, repository_id: str, tag: str) -> InstallationResult:
        pass

    @abstractmethod
    async def uninstall(self, extension_id: str) -> None:
        pass


class Content(ABC):
    def __init__(self, path: Path):
        self.path = path

    @property
    @abstractmethod
    def content_type(self) -> str:
        pass


class ContentDiscovery(ABC):

    @abstractmethod
    def matches(self, path: Path) -> bool:
        pass

    @abstractmethod
    def create(self, path: Path) -> Content:
        pass
