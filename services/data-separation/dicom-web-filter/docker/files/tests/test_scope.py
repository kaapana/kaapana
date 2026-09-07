"""Pins the project-scoping contract of the DICOMweb read routes.

No Project header means all of the user's memberships (unscoped dcmweb
tooling); a header narrows reads to that project alone; admins may read-scope
to any project; an unparseable header is a 400, never a silent widening.
"""

import json
import logging
from uuid import UUID

import pytest
from app.utils import get_scoped_project_ids, is_unscoped_admin
from fastapi import HTTPException

PROJECT_A = "11111111-1111-1111-1111-111111111111"
PROJECT_B = "22222222-2222-2222-2222-222222222222"
FOREIGN = "33333333-3333-3333-3333-333333333333"


def header(project_id: str) -> str:
    return json.dumps({"id": project_id})


def test_without_header_reads_span_all_memberships(make_request):
    request = make_request(projects=[PROJECT_A, PROJECT_B])

    assert get_scoped_project_ids(request) == [UUID(PROJECT_A), UUID(PROJECT_B)]


def test_header_narrows_reads_to_the_selected_project(make_request):
    request = make_request(header(PROJECT_B), projects=[PROJECT_A, PROJECT_B])

    assert get_scoped_project_ids(request) == [UUID(PROJECT_B)]


def test_non_member_cannot_scope_to_a_foreign_project(make_request):
    request = make_request(header(FOREIGN), projects=[PROJECT_A])

    with pytest.raises(HTTPException) as exc:
        get_scoped_project_ids(request)
    assert exc.value.status_code == 403


def test_admin_may_scope_to_a_project_they_are_no_member_of(make_request):
    request = make_request(header(FOREIGN), projects=[PROJECT_A], admin=True)

    assert get_scoped_project_ids(request) == [UUID(FOREIGN)]


@pytest.mark.parametrize(
    "raw", ["not json", '"abc"', '{"project": "a"}', '{"id": "not-a-uuid"}']
)
def test_unparseable_header_is_rejected_and_logged(make_request, caplog, raw):
    request = make_request(raw, projects=[PROJECT_A])

    with caplog.at_level(logging.WARNING, logger="app.utils"):
        with pytest.raises(HTTPException) as exc:
            get_scoped_project_ids(request)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid Project header"
    warnings = [
        r
        for r in caplog.records
        if r.name == "app.utils" and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert raw in warnings[0].getMessage()


def test_only_admins_without_a_project_context_see_everything(make_request):
    assert is_unscoped_admin(make_request(projects=[PROJECT_A], admin=True))
    assert not is_unscoped_admin(
        make_request(header(PROJECT_A), projects=[PROJECT_A], admin=True)
    )
    assert not is_unscoped_admin(make_request(projects=[PROJECT_A]))
