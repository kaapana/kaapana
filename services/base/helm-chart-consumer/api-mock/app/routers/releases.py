from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Query, status

from .. import examples
from ..models import DryRunResult, Error, Release, ReleaseCreate, ReleaseState

router = APIRouter(tags=["Releases"])

CREATE_EXAMPLES = {
    "project": {"summary": "In a project", "value": examples.DEPLOY_REQUEST},
}


@router.get("/releases")
def list_releases(
    project_id: Annotated[str | None, Query(description="Only releases of this project.")] = None,
    name: Annotated[str | None, Query(description="Only releases with this name.")] = None,
    application_id: str | None = None,
    version: Annotated[str | None, Query(description="Only releases of this version of the application.")] = None,
    state: Annotated[list[ReleaseState] | None, Query()] = None,
    deployed_for: Annotated[str | None, Query(description="Only releases meant for this user.")] = None,
) -> list[Release]:
    """List releases, newest first.

    Users see the releases of their projects. Only a kaapana-system-admin sees all releases. Helm
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
    the deploy would set.
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
            "description": "A parameter is invalid, or the helm dry-run failed.",
        },
        403: {
            "model": Error,
            "description": "The user may not deploy with this placement, or the origin does not match the caller.",
        },
        409: {
            "model": Error,
            "description": "The name is taken, the application is not enabled in the project, the application or "
            "the version is not registered, or the limit of releases is reached. An application that is not "
            "multi-deployable has at most one release per project.",
        },
    },
)
def create_release(
    release: Annotated[ReleaseCreate, Body(openapi_examples=CREATE_EXAMPLES)],
) -> Release:
    """Deploy an application.

    Principal investigators deploy in their projects, and kaapana-system-admins deploy in every
    project. The application must be enabled in the project. An application that is not
    multi-deployable has at most one release per project. All its versions count toward this
    limit.

    The origin records who deploys. Without an origin in the request, the release gets
    a user origin with the calling user. A user origin that names another user is rejected.

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
