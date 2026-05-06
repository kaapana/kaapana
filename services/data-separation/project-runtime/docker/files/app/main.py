import os
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator


WORKFLOW_DATA_DIR = Path(os.getenv("WORKFLOW_DATA_DIR", "/kaapana/mounted/data"))


class ScaleRule(BaseModel):
    mode: str
    target_dir: Optional[str] = ""
    target_regex: Optional[str] = ".*"
    target_glob: Optional[str] = "*"


class MeasureRequest(BaseModel):
    claim_name: str = Field(default="workflow-data-pv-claim")
    sub_path: str
    scale_rule: ScaleRule

    @field_validator("sub_path")
    @classmethod
    def validate_sub_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("sub_path must be relative and must not contain '..'")
        return value


class MeasureResponse(BaseModel):
    target_size: int


app = FastAPI(title="Project Runtime", version="0.0.1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/filesystem/measure", response_model=MeasureResponse)
def measure(request: MeasureRequest):
    if request.claim_name != "workflow-data-pv-claim":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported claim_name: {request.claim_name}",
        )

    channel_path = _resolve_under_root(WORKFLOW_DATA_DIR, request.sub_path)
    target_path = _resolve_under_root(channel_path, request.scale_rule.target_dir or "")

    if not target_path.exists():
        return MeasureResponse(target_size=0)

    if request.scale_rule.mode == "sum":
        target_size = _sum_of_file_sizes(
            target_path=target_path,
            target_glob=request.scale_rule.target_glob or "*",
            target_regex=request.scale_rule.target_regex or ".*",
        )
    elif request.scale_rule.mode == "max_file_size":
        target_size = _max_file_size(
            target_path=target_path,
            target_glob=request.scale_rule.target_glob or "*",
            target_regex=request.scale_rule.target_regex or ".*",
        )
    elif request.scale_rule.mode == "max_item_sum":
        item_paths = [path for path in channel_path.glob("*") if path.is_dir()]
        target_size = max(
            [
                _sum_of_file_sizes(
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


def _resolve_under_root(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=400, detail="Path escapes mounted volume")
    return path


def _sum_of_file_sizes(
    target_path: Path, target_glob: str = "*", target_regex: str = ".*"
) -> int:
    target_size = 0
    pattern = re.compile(target_regex)
    for file_path in target_path.rglob(target_glob):
        if file_path.is_file() and pattern.fullmatch(
            str(file_path.relative_to(target_path))
        ):
            target_size += file_path.stat().st_size
    return target_size


def _max_file_size(
    target_path: Path, target_glob: str = "*", target_regex: str = ".*"
) -> int:
    target_size = 0
    pattern = re.compile(target_regex)
    for file_path in target_path.rglob(target_glob):
        if file_path.is_file() and pattern.fullmatch(
            str(file_path.relative_to(target_path))
        ):
            target_size = max(file_path.stat().st_size, target_size)
    return target_size
