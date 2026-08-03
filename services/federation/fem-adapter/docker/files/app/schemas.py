from typing import Optional

from pydantic import BaseModel


class SubmitRunRequest(BaseModel):
    """
    Body of POST /fem/submit_run.

    This shape is a working assumption, not a conformance claim: EUCAIM's
    real {project}-fem-client-config schema for the FEM-client -> Federated
    Data Node API is restricted-access and not available while building this
    prototype. It intentionally mirrors the placeholders FEM-client's
    run_tool.resolve_cmd_placeholders() already resolves for every
    submit_run command (task_id, execution_id, user_id, node_name,
    sandbox_host, sandbox_fem, data_path, token) plus the assembled shell
    command (%%TASK_COMMAND%%), so the FEM-client's json_launcher.json
    submit_run.cmd can build this payload without any new resolution logic.
    """

    execution_id: str
    task_id: str
    user_id: str
    command: str
    node_name: Optional[str] = None
    sandbox_host: Optional[str] = None
    sandbox_fem: Optional[str] = None
    data_path: Optional[str] = None
    token: Optional[str] = None


class SubmitRunResponse(BaseModel):
    status: str
    execution_id: str
    workflow_run_id: int
    external_id: Optional[str] = None
    task_id: str


class StatusResponse(BaseModel):
    status: str
    execution_id: str
    workflow_run_id: int
    external_id: Optional[str] = None
