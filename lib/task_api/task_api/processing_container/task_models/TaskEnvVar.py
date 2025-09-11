from __future__ import annotations

from pydantic import BaseModel


class TaskEnvVar(BaseModel):
    """ """

    name: str
    value: str
