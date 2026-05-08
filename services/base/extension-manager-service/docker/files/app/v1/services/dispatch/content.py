from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class InstallationResult:
    success: bool
    message: str | None = None


class Content(BaseModel):
    name: str
    content_type: str
    path: Path


class ContentInstaller(ABC):
    @abstractmethod
    def can_install(self, content: Content) -> bool:
        pass

    @abstractmethod
    async def install(self, content: Content) -> InstallationResult:
        pass

    @abstractmethod
    async def uninstall(self, content: Content) -> None:
        pass
