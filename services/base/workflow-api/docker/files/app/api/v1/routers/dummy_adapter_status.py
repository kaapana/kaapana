from math import log
from fastapi import APIRouter
import logging
from app.adapters.adapters.dummy_adapter import DummyAdapter
from app import schemas

"""
Router for DummyAdapter test endpoints, useful for integration tests.
Allows setting and resetting workflow run statuses in the DummyAdapter.
This router is only included when ENABLE_TEST_ADAPTER env var is set to True.
"""

router = APIRouter(
    prefix="/adapter-test",
    tags=["test"],
)

logger = logging.getLogger(__name__)


@router.post("/set-status/{external_id}")
async def set_status(external_id: str, body: dict):
    logger.info(f"DummyAdapter: Setting status for {external_id} to {body['status']}")
    status = schemas.WorkflowRunStatus(body["status"])
    DummyAdapter.set_status(external_id, status)
    return {"ok": True}


@router.post("/reset")
async def reset():
    logger.info("DummyAdapter: Resetting statuses")
    DummyAdapter.reset_statuses()
    return {"ok": True}
