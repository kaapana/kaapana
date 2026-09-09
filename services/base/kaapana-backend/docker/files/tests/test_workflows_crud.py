"""
Unit test for kaapana-backend job creation.

Guards that create_job and put_workflow_jobs never read the owner's job
collection (kaapana_instance.jobs / workflow.workflow_jobs): appending to it
lazy-loads every job of that instance or workflow, >100k rows per created job
on long-running sites (kaapana#2283). No database: the session is mocked.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

# Stub heavy dependencies not installed in the test environment
for mod in (
    "app.config",
    "app.database",
    "app.dependencies",
    "app.workflows.models",
    "app.workflows.utils",
    "cryptography",
    "cryptography.fernet",
    "fastapi",
    "httpx",
    "psycopg2",
    "psycopg2.errors",
    "sqlalchemy",
    "sqlalchemy.exc",
    "sqlalchemy.orm",
):
    sys.modules.setdefault(mod, MagicMock())
# Job rows are plain objects so the foreign key written by crud is visible
sys.modules["app.workflows.models"].Job = lambda **cols: SimpleNamespace(**cols)

import app.workflows.crud as crud  # noqa: E402


class _Row:
    """Instance or workflow row; reading its job collection is the bug."""

    remote = True
    workflow_id = "wf"

    @property
    def jobs(self):
        raise AssertionError("job collection loaded")

    workflow_jobs = jobs


def test_job_creation_does_not_load_job_collections():
    db = MagicMock()
    first = db.query.return_value.filter_by.return_value.first
    first.return_value = _Row()

    job = crud.schemas.JobCreate(kaapana_instance_id=1, dag_id="dag")
    db_job = crud.create_job(db, job)
    db.add.assert_called_once_with(db_job)

    first.side_effect = [_Row(), db_job]  # get_workflow, then get_job
    update = crud.schemas.WorkflowUpdate(workflow_id="wf", workflow_jobs=[{"id": 1}])
    crud.put_workflow_jobs(db, update)
    assert db_job.workflow_id == "wf"
