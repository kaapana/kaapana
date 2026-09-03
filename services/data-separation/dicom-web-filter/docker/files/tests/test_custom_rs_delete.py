"""Tests for the CUSTOM_RS delete routes of the dicom-web-filter."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import Request

from app.CUSTOM_RS import routes


def test_del_study_allows_admin_token_without_project_claim(monkeypatch):
    """The internal system user has the admin role but no project claims."""
    monkeypatch.setattr(routes, "assert_project_not_archived", AsyncMock())
    routes.crud.get_series_instance_uids_of_study_which_are_mapped_to_projects.return_value = []
    routes.crud.get_all_series_of_study.return_value = []
    request = Request(
        {"type": "http", "headers": [], "admin": True, "token": {"projects": []}}
    )

    response = asyncio.run(
        routes.del_study(
            project_id=uuid4(),
            study="1.2.3",
            request=request,
            session=None,
            project_ids_of_user=[],
        )
    )

    assert response.status_code == 200
