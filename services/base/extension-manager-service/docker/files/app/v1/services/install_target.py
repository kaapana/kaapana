import enum
import uuid
from dataclasses import dataclass
from typing import Optional

from semver import Version
from v1.services.database.models import ExtensionStatus
from v1.services.logger import get_logger

logger = get_logger(__name__)


class InstallTargetKind(enum.StrEnum):
    INSTALL = "install"
    UPDATE = "update"


@dataclass
class ActiveExtension:
    id: uuid.UUID
    status: ExtensionStatus
    version: str
    pending_version: Optional[str]
    same_repository: bool
    same_tag: bool


@dataclass
class InstallTarget:
    kind: InstallTargetKind
    extension_id: Optional[uuid.UUID] = None


class InstallConflictError(Exception):
    pass


def resolve_install_target(active: Optional[ActiveExtension], requested_version: str) -> InstallTarget:
    """`active` is the extension with the same manifest id that is not uninstalled.

    Raises ValueError for a version that is not semver and InstallConflictError for one that cannot be used.
    """
    requested = Version.parse(requested_version)

    if active is None:
        return InstallTarget(InstallTargetKind.INSTALL)

    if active.same_repository and active.same_tag:
        return InstallTarget(InstallTargetKind.INSTALL, active.id)

    if active.status not in (ExtensionStatus.INSTALLED, ExtensionStatus.UPDATE_FAILED):
        raise InstallConflictError(
            f"The extension is in status {active.status} with version {active.version}. Uninstall it first."
        )

    if not active.same_repository:
        raise InstallConflictError(
            f"The extension is installed in version {active.version} from another repository. "
            "A newer version must come from that repository, or uninstall it first."
        )

    comparison = requested.compare(active.version)
    if comparison == 0:
        raise InstallConflictError(
            f"The extension is already installed in version {active.version}. "
            "Install a newer version, or uninstall it first."
        )
    if comparison < 0:
        raise InstallConflictError(
            f"The extension is installed in version {active.version}; downgrading to {requested_version} is not supported."
        )
    if (
        active.status == ExtensionStatus.UPDATE_FAILED
        and active.pending_version is not None
        and requested.compare(active.pending_version) < 0
    ):
        logger.warning(
            "An update to %s failed; contents already on it are patched back to %s",
            active.pending_version,
            requested_version,
        )
    return InstallTarget(InstallTargetKind.UPDATE, active.id)
