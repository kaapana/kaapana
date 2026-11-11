from fastapi import APIRouter, status

from ..models import Error

router = APIRouter(tags=["Projects"])


@router.put(
    "/projects/{project_id}/enabled-applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": Error},
        404: {"model": Error, "description": "The project or the application does not exist."},
    },
)
def enable_application(project_id: str, application_id: str) -> None:
    """Enable an application in a project. Only a kaapana-system-admin may do this.

    An enablement covers all registered versions of the application. Enabling an application
    that is already enabled changes nothing. `GET /applications?project_id=<id>` lists the
    applications that are enabled in a project.
    """


@router.delete(
    "/projects/{project_id}/enabled-applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": Error},
        404: {"model": Error, "description": "The project or the application does not exist."},
    },
)
def disable_application(project_id: str, application_id: str) -> None:
    """Disable an application in a project. Only a kaapana-system-admin may do this.

    Existing releases of the application keep running. Disabling an application that is not
    enabled changes nothing.
    """
