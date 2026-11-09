from typing import Optional
from unittest.mock import patch
from uuid import uuid4

import pytest
from v1.services.database.models import ExtensionStatus
from v1.services.install_target import (
    ActiveExtension,
    InstallConflictError,
    InstallTargetKind,
    resolve_install_target,
)


def _active(
    status: ExtensionStatus = ExtensionStatus.INSTALLED,
    version: str = "1.0.0",
    pending_version: Optional[str] = None,
    same_repository: bool = True,
    same_tag: bool = False,
) -> ActiveExtension:
    return ActiveExtension(
        id=uuid4(),
        status=status,
        version=version,
        pending_version=pending_version,
        same_repository=same_repository,
        same_tag=same_tag,
    )


def test_no_active_extension_is_installed():
    target = resolve_install_target(None, "1.0.0")
    assert target.kind == InstallTargetKind.INSTALL
    assert target.extension_id is None


@pytest.mark.parametrize("version", ["1.0", "v1.0.0", "latest"])
def test_invalid_version_is_rejected(version: str):
    with pytest.raises(ValueError):
        resolve_install_target(None, version)


def test_higher_version_from_the_same_repository_updates():
    active = _active()
    target = resolve_install_target(active, "1.1.0")
    assert target.kind == InstallTargetKind.UPDATE
    assert target.extension_id == active.id


@pytest.mark.parametrize("status", [ExtensionStatus.INSTALLED, ExtensionStatus.UPDATE_FAILED])
def test_version_from_another_repository_conflicts(status: ExtensionStatus):
    active = _active(status, pending_version="2.0.0", same_repository=False)
    with pytest.raises(InstallConflictError, match="from another repository"):
        resolve_install_target(active, "2.1.0")


def test_same_version_under_another_tag_conflicts():
    with pytest.raises(InstallConflictError, match="already installed in version 1.0.0"):
        resolve_install_target(_active(), "1.0.0")


def test_lower_version_conflicts():
    with pytest.raises(InstallConflictError, match="downgrading"):
        resolve_install_target(_active(version="2.0.0"), "1.0.0")


@pytest.mark.parametrize("requested", ["2.0.0", "2.0.1"])
def test_update_failed_retries_or_moves_to_a_newer_target(requested: str):
    active = _active(ExtensionStatus.UPDATE_FAILED, pending_version="2.0.0")
    target = resolve_install_target(active, requested)
    assert target.kind == InstallTargetKind.UPDATE
    assert target.extension_id == active.id


def test_update_failed_allows_version_below_failed_target_with_a_warning():
    active = _active(ExtensionStatus.UPDATE_FAILED, pending_version="2.0.0")
    with patch("v1.services.install_target.logger") as logger:
        target = resolve_install_target(active, "1.5.0")
    assert target.kind == InstallTargetKind.UPDATE
    logger.warning.assert_called_once()


def test_update_failed_rejects_the_installed_version():
    active = _active(ExtensionStatus.UPDATE_FAILED, pending_version="2.0.0")
    with pytest.raises(InstallConflictError, match="already installed in version 1.0.0"):
        resolve_install_target(active, "1.0.0")


@pytest.mark.parametrize("status", list(ExtensionStatus))
def test_the_same_repository_and_tag_takes_the_install_path(status: ExtensionStatus):
    active = _active(status, same_tag=True)
    target = resolve_install_target(active, "1.0.0")
    assert target.kind == InstallTargetKind.INSTALL
    assert target.extension_id == active.id


@pytest.mark.parametrize(
    "status", [ExtensionStatus.INSTALLATION_FAILED, ExtensionStatus.UPDATING, ExtensionStatus.UNINSTALLING]
)
@pytest.mark.parametrize(("same_repository", "same_tag"), [(True, False), (False, True), (False, False)])
def test_other_status_with_another_repository_or_tag_conflicts(
    status: ExtensionStatus, same_repository: bool, same_tag: bool
):
    active = _active(status, same_repository=same_repository, same_tag=same_tag)
    with pytest.raises(InstallConflictError, match="Uninstall it first"):
        resolve_install_target(active, "1.1.0")
