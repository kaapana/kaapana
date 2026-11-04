import enum
from dataclasses import dataclass
from typing import Optional

from v1.services.database.models import ContentStatus
from v1.services.oci.models import ExtensionManifest


class ContentAction(enum.StrEnum):
    INSTALL = "install"
    UPDATE = "update"
    UNINSTALL = "uninstall"
    SKIP = "skip"


@dataclass
class InstalledContentState:
    name: str
    content_type: str
    status: ContentStatus
    applied_version: Optional[str] = None


class ContentTypeChangedError(Exception):
    """Raised when a content keeps its name but changes its type, which no installer can update."""


def plan_content_changes(
    installed: list[InstalledContentState],
    target: ExtensionManifest,
) -> list[tuple[str, ContentAction]]:
    """Match contents by name; one already at the target version is skipped, so a retry only touches what is still old."""
    installed_by_name = {content.name: content for content in installed}
    target_names = {content.name for content in target.contents}
    changes: list[tuple[str, ContentAction]] = []

    for target_content in target.contents:
        current = installed_by_name.get(target_content.name)
        if current is None or current.applied_version is None or current.status == ContentStatus.UNINSTALLED:
            changes.append((target_content.name, ContentAction.INSTALL))
        elif current.content_type != target_content.contentType:
            raise ContentTypeChangedError(
                f"Content {target_content.name} changes its type from {current.content_type} "
                f"to {target_content.contentType}"
            )
        elif current.applied_version == target.version:
            changes.append((target_content.name, ContentAction.SKIP))
        else:
            changes.append((target_content.name, ContentAction.UPDATE))

    for current in installed:
        if current.name in target_names:
            continue
        if current.status == ContentStatus.UNINSTALLED:
            changes.append((current.name, ContentAction.SKIP))
        else:
            changes.append((current.name, ContentAction.UNINSTALL))

    return changes
