from typing import List, Optional

import requests
from kaapanapy.settings import ServicesSettings
from pydantic import BaseModel

NOTIFICATION_SERVICE_URL = ServicesSettings().notification_url


class Notification(BaseModel):
    topic: Optional[str] = None
    title: str
    description: str
    icon: Optional[str] = None
    link: Optional[str] = None


class NotificationService:
    @staticmethod
    def send(project_id: str, user_ids: List[str], notification: Notification) -> None:
        data = notification.model_dump()
        if not user_ids:
            response = requests.post(
                f"{NOTIFICATION_SERVICE_URL}/v1/{project_id}",
                json=data,
            )
        else:
            data["receivers"] = user_ids
            response = requests.post(
                f"{NOTIFICATION_SERVICE_URL}/v1/",
                json=data,
            )
        response.raise_for_status()
