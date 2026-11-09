from typing import Annotated

from fastapi import APIRouter, Body, Query, status
from fastapi.responses import PlainTextResponse

from .. import examples
from ..models import (
    Deployment,
    DeploymentCreate,
    DeploymentState,
    DeploymentStatus,
    DeploymentUpdate,
    DryRunResult,
    Error,
    Scope,
)

router = APIRouter(tags=["Deployments"])

CREATE_EXAMPLES = {
    "project": {"summary": "In a project", "value": examples.DEPLOY_REQUEST},
    "platform": {"summary": "Platform-wide", "value": examples.PLATFORM_DEPLOY_REQUEST},
}
UPDATE_EXAMPLES = {"jupyterlab": {"value": examples.UPDATE_REQUEST}}


@router.get("/deployments")
def list_deployments(
    project_id: Annotated[str | None, Query(description="Only deployments of this project.")] = None,
    scope: Annotated[Scope | None, Query(description="Only project or only platform-wide deployments.")] = None,
    name: Annotated[str | None, Query(description="Only deployments with this name.")] = None,
    application_id: str | None = None,
    version: Annotated[str | None, Query(description="Only deployments of this version of the application.")] = None,
    state: Annotated[list[DeploymentState] | None, Query()] = None,
    deployed_for: Annotated[str | None, Query(description="Only deployments meant for this user.")] = None,
    from_workflow: Annotated[
        bool | None,
        Query(description="True lists only deployments that a workflow started. False lists only the others."),
    ] = None,
    workflow_run_id: Annotated[str | None, Query(description="Only deployments started by this workflow run.")] = None,
) -> list[Deployment]:
    """List deployments, newest first.

    Users see the deployments of their projects and all platform-wide deployments. A
    kaapana-system-admin sees all deployments. Platform-wide deployments never belong to a project.

    Filter by `project_id` to find out whether a project still has deployments, for example before
    the project is deleted.
    """
    return examples.DEPLOYMENTS


@router.post(
    "/deployments/dry-run",
    responses={403: {"model": Error, "description": "The user may not deploy with this placement."}},
)
def check_deployment(
    deployment: Annotated[DeploymentCreate, Body(openapi_examples=CREATE_EXAMPLES)],
) -> DryRunResult:
    """Run every check of a deploy and a helm dry-run installation, but deploy nothing.

    The result lists all problems, not only the first one. It also contains the chart values that
    helm would receive.
    """
    return examples.DRY_RUN_PASSED


@router.post(
    "/deployments",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "headers": {
                "Location": {
                    "description": "Path of the new deployment relative to /v1, e.g. /deployments/d11.",
                    "schema": {"type": "string"},
                }
            }
        },
        400: {
            "model": Error,
            "description": "A parameter is invalid, the application does not support the scope of the placement, "
            "or the helm dry-run failed.",
        },
        403: {"model": Error, "description": "The user may not deploy with this placement."},
        409: {
            "model": Error,
            "description": "The name is taken, the application is not enabled in the project, the application or "
            "the version is not registered, or the limit of deployments is reached. The limit is one per project for "
            "an application that is not multi-deployable, and one platform-wide for every application.",
        },
    },
)
def create_deployment(
    deployment: Annotated[DeploymentCreate, Body(openapi_examples=CREATE_EXAMPLES)],
) -> Deployment:
    """Deploy an application.

    Principal investigators deploy in their projects, and kaapana-system-admins deploy in every
    project. Only a kaapana-system-admin deploys platform-wide, and only applications that
    support the platform scope. In a project, the application must be enabled. An application
    that is not multi-deployable has at most one deployment per project, and all its versions
    count toward this limit. Every application has at most one platform-wide deployment.

    The parameter values are validated against the parameter declarations of the version and
    mapped onto chart values. Chart values that are not declared cannot be set. The deploy runs
    the same checks as `POST /deployments/dry-run`, including the helm dry-run, before it creates
    the helm release. If a check fails, nothing is deployed.

    The new deployment starts in state `deploying`. Poll it until the state is `ready` or `failed`.
    """
    return examples.NEW_DEPLOYMENT


@router.get("/deployments/{deployment_id}", responses={404: {"model": Error}})
def get_deployment(deployment_id: str) -> Deployment:
    """Get one deployment with its configuration. Secret values are never returned."""
    return examples.ANNA_NOTEBOOK


@router.post(
    "/deployments/{deployment_id}/dry-run",
    responses={403: {"model": Error}, 404: {"model": Error}},
)
def check_update(
    deployment_id: str,
    update: Annotated[DeploymentUpdate, Body(openapi_examples=UPDATE_EXAMPLES)],
) -> DryRunResult:
    """Run every check of an update and a helm dry-run upgrade, but change nothing."""
    return examples.UPDATE_DRY_RUN_PASSED


@router.patch(
    "/deployments/{deployment_id}",
    responses={
        400: {"model": Error, "description": "A parameter is invalid, or the helm dry-run failed."},
        403: {"model": Error},
        404: {"model": Error},
        409: {"model": Error, "description": "The deployment is busy, or the target version is not registered."},
    },
)
def update_deployment(
    deployment_id: str,
    update: Annotated[DeploymentUpdate, Body(openapi_examples=UPDATE_EXAMPLES)],
) -> Deployment:
    """Change the version or the parameters of a deployment.

    Parameters that exist in the old and the new version keep their values unless the request
    changes them. New parameters get their defaults, and parameters the new version no longer
    declares are dropped. The parameters of a deployment whose version was deregistered can still
    be changed, because the Helm Chart Consumer keeps the chart and the declarations of every
    deployment. Persistent volumes are kept.

    The update runs the same checks as `POST /deployments/{deployment_id}/dry-run` first. If a
    check fails, nothing changes. Otherwise the deployment shows the requested version and
    parameters at once, and it is in state `updating` until the upgrade finishes.
    """
    return examples.ANNA_NOTEBOOK_UPDATING


@router.delete(
    "/deployments/{deployment_id}",
    status_code=status.HTTP_202_ACCEPTED,
    responses={403: {"model": Error}, 404: {"model": Error}},
)
def delete_deployment(deployment_id: str) -> Deployment:
    """Undeploy a deployment.

    This removes the helm release, all Kubernetes resources it created and the persistent volumes
    with their data. The deployment is in state `undeploying` until everything is removed, then it
    is gone. Repeating the request while it is undeploying changes nothing. Once the deployment is
    gone, the request answers 404. A client that retries can take this 404 as success.

    A deployment whose helm release was removed outside the Helm Chart Consumer is undeployed the
    same way. This removes what is left of it, such as its volumes, and then the deployment itself.
    """
    return examples.ANNA_NOTEBOOK_UNDEPLOYING


@router.get("/deployments/{deployment_id}/status", responses={404: {"model": Error}})
def get_deployment_status(deployment_id: str) -> DeploymentStatus:
    """Get the pods and Kubernetes events of a deployment, and the helm error if a helm command failed."""
    return examples.ANNA_NOTEBOOK_STATUS


@router.get(
    "/deployments/{deployment_id}/logs",
    response_class=PlainTextResponse,
    responses={
        403: {"model": Error, "description": "Only principal investigators and kaapana-system-admins see logs."},
        404: {"model": Error, "description": "Unknown deployment, pod or container."},
    },
)
def get_deployment_logs(
    deployment_id: str,
    pod: Annotated[str | None, Query(description="The first pod if omitted.")] = None,
    container: Annotated[str | None, Query(description="The first container if omitted.")] = None,
    tail: Annotated[int, Query(ge=1, le=5000)] = 200,
) -> str:
    """Get the last log lines of one container of a deployment."""
    return examples.ANNA_NOTEBOOK_LOGS


@router.post(
    "/deployments/{deployment_id}/complete",
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": Error}, 409: {"model": Error, "description": "No workflow started the deployment."}},
)
def complete_deployment(deployment_id: str) -> Deployment:
    """Report that the user finished the work in a deployment that a workflow started.

    Every member of the project may call this. The waiting workflow task continues with the
    results the user saved to the project storage, and the deployment is undeployed. Repeating
    the request while it is undeploying changes nothing. Once the deployment is gone, the request
    answers 404. A client that retries can take this 404 as success.
    """
    return examples.ANNA_NOTEBOOK_UNDEPLOYING
