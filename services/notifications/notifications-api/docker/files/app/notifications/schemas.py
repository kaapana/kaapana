import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

# class OrmBaseModel(BaseModel):
#     model_config = ConfigDict(from_attributes=True)


class NotificationType(str, Enum):
    Error = "error"
    Warning = "warning"
    Update = "update"
    Others = "others"


class Notification(BaseModel):
    topic: str
    message: str
    type: NotificationType


class NotificationDispatch(Notification):
    id: uuid.UUID
    project: Optional[str]
    user_id: Optional[str]
    timestamp: datetime


class NotificationDispatchResponse(BaseModel):
    notification_id: uuid.UUID
    success: bool
    active_connections: int
    total_dispatched: int
    timestamp: datetime
