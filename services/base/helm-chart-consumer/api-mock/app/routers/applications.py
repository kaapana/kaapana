from typing import Annotated, Any

from fastapi import APIRouter, Body, Query, status

from .. import examples
from ..models import Application, ApplicationVersion, Error, HelmChartContent, Scope, VersionRegistration

router = APIRouter(tags=["Applications"])

REGISTRATION_LOCATION = {
    "description": "Path of the version relative to /v1, e.g. /applications/jupyterlab/versions/4.3.0. "
    "The Extension Manager appends it to its base URL, which ends in /v1.",
    "schema": {"type": "string"},
}


@router.get("/applications")
def list_applications(
    project_id: Annotated[
        str | None,
        Query(description="Only applications that are enabled in this project and support the project scope."),
    ] = None,
    scope: Annotated[Scope | None, Query(description="Only applications that support this scope.")] = None,
) -> list[Application]:
    """List the applications that have at least one registered version.

    Users see each helm-chart content as an application. Its name, description and scopes come
    from its newest registered version.

    A kaapana-system-admin sees all applications. Every other user sees only the applications
    that are enabled in at least one of their projects.
    """
    return examples.APPLICATIONS


@router.get("/applications/{application_id}", responses={404: {"model": Error}})
def get_application(application_id: str) -> Application:
    """Get one application with its registered versions."""
    return examples.APPLICATIONS[0]


@router.get("/applications/{application_id}/versions", responses={404: {"model": Error}})
def list_versions(
    application_id: str,
    include_deregistered: Annotated[
        bool, Query(description="Also list versions that releases still run after their extension was uninstalled.")
    ] = False,
) -> list[ApplicationVersion]:
    """List the versions of an application, newest first.

    Several versions of one application can be registered at the same time.
    """
    return examples.JUPYTERLAB_VERSIONS


@router.get("/applications/{application_id}/versions/{version}", responses={404: {"model": Error}})
def get_version(application_id: str, version: str) -> ApplicationVersion:
    """Get one version with its deploy parameters.

    `content.parameters` declares which values a deploy accepts, with their types, limits and
    defaults. Deregistered versions stay readable while releases run them, so that their
    parameters can still be changed.
    """
    return examples.JUPYTERLAB_VERSIONS[0]


@router.put(
    "/applications/{application_id}/versions/{version}",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"headers": {"Location": REGISTRATION_LOCATION}},
        200: {
            "model": ApplicationVersion,
            "description": "The same registration was already stored.",
            "headers": {"Location": REGISTRATION_LOCATION},
        },
        400: {
            "model": Error,
            "description": "The content or the chart is invalid. The detail says why, in words meant for the "
            "person who installs the extension.",
        },
        409: {
            "model": Error,
            "description": "This name and version are already stored with another content or for another extension.",
        },
    },
)
def register_version(
    application_id: str,
    version: str,
    registration: Annotated[
        VersionRegistration, Body(openapi_examples={"jupyterlab": {"value": examples.REGISTRATION_REQUEST}})
    ],
) -> ApplicationVersion:
    """Register a version of a helm-chart content. The Extension Manager calls this when it installs an extension.

    The Helm Chart Consumer fetches the chart from `chart_reference`. It validates `content`
    against the schema of `helm-chart-content.json` and checks the chart with `helm lint`.
    `application_id` must equal `content.name`, and `version` must equal the version of the
    extension. If a check fails, the route answers 400. Repeating the same registration changes
    nothing and answers 200, so the Extension Manager can retry. A registration that differs from
    the stored one answers 409. This also holds for a deregistered version that releases still
    run, because they depend on the stored chart. To deregister the version, the Extension Manager
    sends DELETE to the path in the `Location` header.

    A newly registered application is disabled in all projects.
    """
    return examples.JUPYTERLAB_VERSIONS[0]


@router.delete(
    "/applications/{application_id}/versions/{version}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deregister_version(application_id: str, version: str) -> None:
    """Deregister a version. The Extension Manager calls this when it uninstalls the extension.

    The version can no longer be deployed. Its releases keep running and are marked with
    `version_registered: false`. Other versions of the application are not affected. Deleting a
    version that is not registered also answers 204, so the Extension Manager can retry.
    """


@router.get("/helm-chart-content-schema")
def get_content_schema() -> dict[str, Any]:
    """Get the JSON schema of `helm-chart-content.json`, which extension developers write."""
    return HelmChartContent.model_json_schema()
