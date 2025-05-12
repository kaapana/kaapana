## Services

You can access multiple services in processing containers.

There is a kaapanapy library package, that should allow you to easily use those services.

### Notification Service

You can send notifications to the user or all users of the project (only within your authorization scope) with the following commands:

```
from kaapanapy.services import NotificationService

NotificationService.post_notification_to_user(
    user_id: str, project_id: str, notification: NotificationCreate
)

NotificationService.post_notification_to_project(
    project_id: str, notification: NotificationCreate
)

class NotificationCreate(BaseModel):
    topic: Optional[str]
    title: str
    description: str
    icon: Optional[str]
    link: Optional[str]
    receivers: list[str]
```