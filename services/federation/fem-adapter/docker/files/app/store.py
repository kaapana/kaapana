"""
In-memory execution_id -> workflow_run_id mapping.

This prototype runs a single fem-adapter process with a single in-memory
dict; a restart loses the mapping. That's an acceptable limitation for the
local sandbox this service is built to prove out. A production deployment
would persist this mapping (or derive it from workflow-api directly, e.g. by
storing the FEM execution_id as a Label on the WorkflowRun) instead of
keeping it in process memory.
"""

_execution_to_run: dict[str, int] = {}


def set_workflow_run_id(execution_id: str, workflow_run_id: int) -> None:
    _execution_to_run[execution_id] = workflow_run_id


def get_workflow_run_id(execution_id: str) -> int | None:
    return _execution_to_run.get(execution_id)
