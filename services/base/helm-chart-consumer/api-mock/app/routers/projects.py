from fastapi import APIRouter, status

from .. import examples
from ..models import Enablement, Error

router = APIRouter(tags=["Projects"])


@router.get("/projects/{project_id}/enabled-applications")
def list_enabled_applications(project_id: str) -> list[Enablement]:
    """List the applications that can be deployed in a project.

    An enablement covers all registered versions of the application.
    """
    return examples.LUNG_CT_ENABLEMENTS


@router.put(
    "/projects/{project_id}/enabled-applications/{application_id}",
    responses={
        400: {"model": Error, "description": "The application supports only the platform scope."},
        403: {"model": Error},
        404: {"model": Error},
    },
)
def enable_application(project_id: str, application_id: str) -> Enablement:
    """Enable an application in a project. Only a kaapana-system-admin may do this.

    Enabling an application that is already enabled changes nothing.
    """
    return examples.LUNG_CT_ENABLEMENTS[0]


@router.delete(
    "/projects/{project_id}/enabled-applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {"model": Error}, 404: {"model": Error, "description": "Unknown project or application."}},
)
def disable_application(project_id: str, application_id: str) -> None:
    """Disable an application in a project. Only a kaapana-system-admin may do this.

    Existing deployments of the application keep running. Disabling an application that is not
    enabled changes nothing.
    """
