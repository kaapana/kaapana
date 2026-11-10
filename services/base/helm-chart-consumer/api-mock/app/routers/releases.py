from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Query, status

from .. import examples
from ..models import (
    DryRunResult,
    Error,
    Release,
    ReleaseCreate,
    ReleaseState,
    ReleaseStatus,
    ReleaseUpdate,
    Scope,
)

router = APIRouter(tags=["Releases"])

CREATE_EXAMPLES = {
    "project": {"summary": "In a project", "value": examples.DEPLOY_REQUEST},
    "platform": {"summary": "Platform-wide", "value": examples.PLATFORM_DEPLOY_REQUEST},
    "workflow": {"summary": "From a workflow task", "value": examples.WORKFLOW_DEPLOY_REQUEST},
}
UPDATE_EXAMPLES = {"jupyterlab": {"value": examples.UPDATE_REQUEST}}


@router.get("/releases")
def list_releases(
    project_id: Annotated[str | None, Query(description="Only releases of this project.")] = None,
    scope: Annotated[Scope | None, Query(description="Only project or only platform-wide releases.")] = None,
    name: Annotated[str | None, Query(description="Only releases with this name.")] = None,
    application_id: str | None = None,
    version: Annotated[str | None, Query(description="Only releases of this version of the application.")] = None,
    state: Annotated[list[ReleaseState] | None, Query()] = None,
    deployed_for: Annotated[str | None, Query(description="Only releases meant for this user.")] = None,
    origin_type: Annotated[
        Literal["user", "workflow"] | None,
        Query(description="The list contains only releases whose origin has this type."),
    ] = None,
    workflow_run_id: Annotated[str | None, Query(description="Only releases started by this workflow run.")] = None,
) -> list[Release]:
    """List releases, newest first.

    Users see the releases of their projects and all platform-wide releases. A
    kaapana-system-admin sees all releases. Platform-wide releases never belong to a project. Helm
    releases that other tools installed are not listed.

    Filter by `project_id` to find out whether a project still has releases, for example before
    the project is deleted.
    """
    return examples.RELEASES


@router.post(
    "/releases/dry-run",
    responses={
        403: {
            "model": Error,
            "description": "The user may not deploy with this placement, or the origin does not match the caller.",
        }
    },
)
def check_release(
    release: Annotated[ReleaseCreate, Body(openapi_examples=CREATE_EXAMPLES)],
) -> DryRunResult:
    """Run every check of a deploy and a helm dry-run installation, but deploy nothing.

    The result lists all problems, not only the first one. It also contains the chart values that
    helm would receive.
    """
    return examples.DRY_RUN_PASSED


@router.post(
    "/releases",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "headers": {
                "Location": {
                    "description": "This is the path of the new release relative to /v1, for example "
                    "/releases/7c1e4b9a-2f6d-4a83-b0c5-9e8d3f1a6b24.",
                    "schema": {"type": "string"},
                }
            }
        },
        400: {
            "model": Error,
            "description": "A parameter is invalid, the application does not support the scope of the placement, "
            "or the helm dry-run failed.",
        },
        403: {
            "model": Error,
            "description": "The user may not deploy with this placement, or the origin does not match the caller.",
        },
        409: {
            "model": Error,
            "description": "The name is taken, the application is not enabled in the project, the application or "
            "the version is not registered, or the limit of releases is reached. An application that is not "
            "multi-deployable has at most one release per project and at most one platform-wide release.",
        },
    },
)
def create_release(
    release: Annotated[ReleaseCreate, Body(openapi_examples=CREATE_EXAMPLES)],
) -> Release:
    """Deploy an application.

    Principal investigators deploy in their projects, and kaapana-system-admins deploy in every
    project. Only a kaapana-system-admin deploys platform-wide, and only applications that
    support the platform scope. In a project, the application must be enabled. An application
    that is not multi-deployable has at most one release per project and at most one
    platform-wide release. All its versions count toward both limits.

    The origin records who or what deploys. Without an origin in the request, the release gets
    a user origin with the calling user. A user origin that names another user is rejected, and
    so is a workflow origin from any caller other than workflow-api.

    The parameter values are validated against the parameter declarations of the version and
    mapped onto chart values. Chart values that are not declared cannot be set. The deploy runs
    the same checks as `POST /releases/dry-run`, including the helm dry-run, before it creates
    the helm release. If a check fails, nothing is deployed.

    The new release starts in state `deploying`. Poll it until the state is `ready` or `failed`.
    """
    return examples.NEW_RELEASE


@router.get("/releases/{release_id}", responses={404: {"model": Error}})
def get_release(release_id: UUID) -> Release:
    """Get one release with its configuration. Secret values are never returned."""
    return examples.ANNA_NOTEBOOK


@router.post(
    "/releases/{release_id}/dry-run",
    responses={403: {"model": Error}, 404: {"model": Error}},
)
def check_update(
    release_id: UUID,
    update: Annotated[ReleaseUpdate, Body(openapi_examples=UPDATE_EXAMPLES)],
) -> DryRunResult:
    """Run every check of an update and a helm dry-run upgrade, but change nothing."""
    return examples.UPDATE_DRY_RUN_PASSED


@router.patch(
    "/releases/{release_id}",
    responses={
        400: {"model": Error, "description": "A parameter is invalid, or the helm dry-run failed."},
        403: {"model": Error},
        404: {"model": Error},
        409: {"model": Error, "description": "The release is busy, or the target version is not registered."},
    },
)
def update_release(
    release_id: UUID,
    update: Annotated[ReleaseUpdate, Body(openapi_examples=UPDATE_EXAMPLES)],
) -> Release:
    """Change the version or the parameters of a release.

    Parameters that exist in the old and the new version keep their values unless the request
    changes them. New parameters get their defaults, and parameters the new version no longer
    declares are dropped. The parameters of a release whose version was deregistered can still
    be changed, because the Helm Chart Consumer keeps the chart and the declarations of every
    release. Persistent volumes are kept.

    The update runs the same checks as `POST /releases/{release_id}/dry-run` first. If a
    check fails, nothing changes. Otherwise the release shows the requested version and
    parameters at once, and it is in state `updating` until the upgrade finishes.
    """
    return examples.ANNA_NOTEBOOK_UPDATING


@router.delete(
    "/releases/{release_id}",
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": Error}, 404: {"model": Error}},
)
def delete_release(release_id: UUID) -> Release:
    """Undeploy a release.

    This removes the helm release, all Kubernetes resources it created and the persistent volumes
    with their data. The release is in state `undeploying` until everything is removed, then it
    is gone. Repeating the request while it is undeploying changes nothing. Once the release is
    gone, the request answers 404. A client that retries can take this 404 as success.

    A release whose helm release was removed outside the Helm Chart Consumer is undeployed the
    same way. This removes what is left of it, such as its volumes, and then the release itself.
    """
    return examples.ANNA_NOTEBOOK_UNDEPLOYING


@router.get("/releases/{release_id}/status", responses={404: {"model": Error}})
def get_release_status(release_id: UUID) -> ReleaseStatus:
    """Get what the cluster reports about a release.

    The result lists every Kubernetes object of the helm release with its readiness. It also lists
    the pods, the events, and the helm error if a helm command failed. To follow the state, poll
    the release itself, which leaves out these details.
    """
    return examples.ANNA_NOTEBOOK_STATUS


@router.post(
    "/releases/{release_id}/complete",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"model": Error},
        409: {"model": Error, "description": "The release has no workflow origin."},
    },
)
def complete_release(release_id: UUID) -> Release:
    """Report that the user finished the work in a release that a workflow started.

    Every member of the project may call this. The waiting workflow task continues with the
    results the user saved to the project storage, and the release is undeployed. Repeating
    the request while it is undeploying changes nothing. Once the release is gone, the request
    answers 404. A client that retries can take this 404 as success.
    """
    return examples.SEGMENTATION_REVIEW_UNDEPLOYING
