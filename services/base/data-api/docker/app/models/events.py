from __future__ import annotations

from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class EventResource(str, Enum):
    DATA_ENTITY = "data_entity"
    METADATA_KEY = "metadata_key"


class EventAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class EventMessage(BaseModel):
    resource: EventResource = Field(..., description="Domain object that changed")
    action: EventAction = Field(..., description="Lifecycle event action")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Event payload for the resource"
    )

    @classmethod
    def build(
        cls, resource: EventResource, action: EventAction, **data: Any
    ) -> "EventMessage":
        return cls(resource=resource, action=action, data=data)
