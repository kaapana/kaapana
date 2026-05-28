from typing import List
from uuid import UUID

import requests
from kaapanapy.helper import get_project_user_access_token
from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings

from .schemas import Project

logger = get_logger(__name__)

_kaapana_settings = KaapanaSettings()
_services_ns = _kaapana_settings.services_namespace

DICOM_WEB_FILTER_URL = f"http://dicom-web-filter-service.{_services_ns}.svc:8080"
AIRFLOW_TRIGGER_URL = (
    f"http://airflow-webserver-service.{_services_ns}.svc:8080"
    "/flow/kaapana/api/trigger/delete-series"
)


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {get_project_user_access_token()}"}


def get_orphan_series(project_id: UUID, admin_project_id: UUID) -> List[str]:
    """
    Series mapped to project_id whose only other mapping (if any) is admin.
    Returns an empty list on HTTP error i.e. "nothing to clean".
    """
    resp = requests.get(
        f"{DICOM_WEB_FILTER_URL}/projects/{project_id}/orphan-series",
        params={"admin_project_id": str(admin_project_id)},
        headers=_auth_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json() or []


def clear_project_mappings(project_id: UUID) -> int:
    """
    Remove every DataProjects row for project_id. Admin-held series remain accessible via the admin project
    """
    resp = requests.delete(
        f"{DICOM_WEB_FILTER_URL}/projects/{project_id}/data",
        headers=_auth_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("deleted", 0)


def trigger_delete_series_dag(admin_project: Project, series_uids: List[str]) -> None:
    """
    Trigger delete-series DAG in admin project's context. 
    """
    if not series_uids:
        return

    payload = {
        "conf": {
            "project_form": {
                "id": str(admin_project.id),
                "opensearch_index": admin_project.opensearch_index,
            },
            "data_form": {"identifiers": list(series_uids)},
            "workflow_form": {
                "delete_complete_study": False,
                "single_execution": False,
            },
        }
    }
    resp = requests.post(AIRFLOW_TRIGGER_URL, json=payload, timeout=30)
    resp.raise_for_status()
