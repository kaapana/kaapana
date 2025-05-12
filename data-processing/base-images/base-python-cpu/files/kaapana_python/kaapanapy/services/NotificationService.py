from typing import Optional

import requests
from kaapanapy.settings import ServicesSettings
from pydantic import BaseModel

NOTIFICATION_SERVICE_URL = ServicesSettings().notification_url


class NotificationCreate(BaseModel):
    topic: Optional[str] = None
    title: str
    description: str
    icon: Optional[str] = None
    link: Optional[str] = None


class NotificationService:
    @staticmethod
    def post_notification_to_user(
        user_id: str, project_id: str, notification: NotificationCreate
    ):
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/v1/{project_id}/{user_id}",
            json=notification.model_dump(),
        )
        response.raise_for_status()
        return response.status_code == 200

    @staticmethod
    def post_notification_to_project(project_id: str, notification: NotificationCreate):
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/v1/{project_id}",
            json=notification.model_dump(),
        )
        response.raise_for_status()
        return response.status_code == 200
