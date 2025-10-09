from typing import List, Optional

import requests
from kaapanapy.settings import ServicesSettings
from kaapanapy.logger import get_logger
from pydantic import BaseModel

NOTIFICATION_SERVICE_URL = ServicesSettings().notification_url
logger = get_logger(__name__)


class Notification(BaseModel):
    topic: Optional[str] = None
    title: str
    description: str
    icon: Optional[str] = None
    link: Optional[str] = None


class NotificationService:
    @staticmethod
    def send(
        notification: Notification, project_id: str, user_ids: List[str] = []
    ) -> None:
        """
        Send a notification to the notification API.
        Send notifications either to all users in a project or to a list of users
        in that project.
        If a user is not a member of the project the notification is send without the project context

        :notification: The notification to send to the API.
        :project_id: The project_id of the project to send notifications to.
        :user_ids: List of user ids to send notifications to.

        """
        data = notification.model_dump()
        if not user_ids:
            response = requests.post(
                f"{NOTIFICATION_SERVICE_URL}/v1/{project_id}",
                json=data,
            )
        else:
            failed_for_users = []
            for user_id in user_ids:
                try:
                    response = requests.post(
                        f"{NOTIFICATION_SERVICE_URL}/v1/{project_id}/{user_id}",
                        json=data,
                    )
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 404:
                        failed_for_users.append(user_id)
                        logger.warning(
                            f"Could not send notification to user with {user_id=} in this project context."
                        )
                    else:
                        raise e
            if failed_for_users:
                data["receivers"] = failed_for_users
                response = requests.post(
                    f"{NOTIFICATION_SERVICE_URL}/v1/",
                    json=data,
                )
        response.raise_for_status()
