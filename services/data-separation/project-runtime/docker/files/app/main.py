import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from task_api.processing_container.pc_models import ScaleRule, ScaleRuleMode
from task_api.processing_container.resources import sum_of_file_sizes, max_file_size


WORKFLOW_DATA_DIR = Path(os.getenv("WORKFLOW_DATA_DIR", "/kaapana/mounted/data"))
SUPPORTED_CLAIM_NAME = "workflow-data-pv-claim"


class FilesystemPathRequest(BaseModel):
    """A claim-scoped, sandboxed path into the mounted workflow-data PVC."""

    claim_name: str = Field(default=SUPPORTED_CLAIM_NAME)
    sub_path: str

    @field_validator("sub_path")
    @classmethod
    def validate_sub_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("sub_path must be relative and must not contain '..'")
        return value


class MeasureRequest(FilesystemPathRequest):
    scale_rule: ScaleRule


class MeasureResponse(BaseModel):
    target_size: int


class DeleteResponse(BaseModel):
    # False if the path did not exist (idempotent no-op); True if it was removed.
    deleted: bool


class UsageResponse(BaseModel):
    exists: bool
    empty: bool
    size_bytes: int


app = FastAPI(title="Project Runtime", version="0.0.1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/filesystem/measure", response_model=MeasureResponse)
def measure(request: MeasureRequest):
    _check_claim(request.claim_name)

    channel_path = _resolve_under_root(WORKFLOW_DATA_DIR, request.sub_path)
    target_path = _resolve_under_root(channel_path, request.scale_rule.target_dir or "")

    if not target_path.exists():
        return MeasureResponse(target_size=0)

    if request.scale_rule.mode == ScaleRuleMode.sum:
        target_size = sum_of_file_sizes(
            target_path=target_path,
            target_glob=request.scale_rule.target_glob or "*",
            target_regex=request.scale_rule.target_regex or ".*",
        )
    elif request.scale_rule.mode == ScaleRuleMode.max_file_size:
        target_size = max_file_size(
            target_path=target_path,
            target_glob=request.scale_rule.target_glob or "*",
            target_regex=request.scale_rule.target_regex or ".*",
        )
    elif request.scale_rule.mode == ScaleRuleMode.max_item_sum:
        item_paths = [path for path in channel_path.glob("*") if path.is_dir()]
        target_size = max(
            [
                sum_of_file_sizes(
                    target_path=_resolve_under_root(
                        item_path, request.scale_rule.target_dir or ""
                    ),
                    target_glob=request.scale_rule.target_glob or "*",
                    target_regex=request.scale_rule.target_regex or ".*",
                )
                for item_path in item_paths
            ],
            default=0,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported scale_rule mode: {request.scale_rule.mode}",
        )

    return MeasureResponse(target_size=target_size)


@app.post("/filesystem/delete", response_model=DeleteResponse)
def delete(request: FilesystemPathRequest):
    """Recursively delete a sub-path of the workflow-data PVC.

    Idempotent: deleting a missing path is a no-op (deleted=False). Refuses to
    delete the volume root so a bug upstream can never wipe the whole PVC.
    """
    _check_claim(request.claim_name)

    target = _resolve_under_root(WORKFLOW_DATA_DIR, request.sub_path)
    if target == WORKFLOW_DATA_DIR.resolve():
        raise HTTPException(
            status_code=400, detail="Refusing to delete the volume root"
        )

    if not target.exists():
        return DeleteResponse(deleted=False)

    shutil.rmtree(target)
    return DeleteResponse(deleted=True)


@app.post("/filesystem/usage", response_model=UsageResponse)
def usage(request: FilesystemPathRequest):
    """Report existence, emptiness and total file size of a PVC sub-path."""
    _check_claim(request.claim_name)

    target = _resolve_under_root(WORKFLOW_DATA_DIR, request.sub_path)
    if not target.exists():
        return UsageResponse(exists=False, empty=True, size_bytes=0)

    empty = target.is_dir() and not any(target.iterdir())
    total = 0
    for entry in target.rglob("*"):
        try:
            if entry.is_file() and not entry.is_symlink():
                total += entry.stat().st_size
        except (FileNotFoundError, PermissionError):
            continue
    return UsageResponse(exists=True, empty=empty, size_bytes=total)


def _check_claim(claim_name: str) -> None:
    if claim_name != SUPPORTED_CLAIM_NAME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported claim_name: {claim_name}",
        )


def _resolve_under_root(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=400, detail="Path escapes mounted volume")
    return path
