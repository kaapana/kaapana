import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


@dataclass
class InstallationResult:
    success: bool
    message: str | None = None
    location: str | None = None


class Content(BaseModel):
    name: str
    content_type: str
    path: Optional[Path] = None
    location: Optional[str] = None
    extension_id: Optional[uuid.UUID] = None
    extension_name: Optional[str] = None
    extension_version: Optional[str] = None


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
