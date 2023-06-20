from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel


class SecurityNotification(BaseModel):
    title: str
    description: Optional[str]
    link: Optional[str]
    timestamp: datetime


class Notification(TypedDict):
    title: str
    description: Optional[str]
    link: Optional[str]
