## Services

You can access Kpapana services in processing containers.

- dicom-web-filter (Access to dcm4chee)
- access-information-interface (Users, Roles, Software and other access control)
- notifications (Send notifications to project or user)
- minio (Store files in the persistent object store)

There is a `kaapanapy` library package, that should allow you to easily use those services.

### Notification Service

You can send notifications to the user (yourself) or project within your authorization scope (project users)
 with the following commands. You can also find example in `templates_and_examples/examples/processing-pipelines/example/processing-containers/notify/files/example-notify.py`

```python
from kaapanapy.services import NotificationService

NotificationService.post_notification_to_user(
    user_id: str, project_id: str, notification: Notification
)

NotificationService.post_notification_to_project(
    project_id: str, notification: Notification
)

class Notification(BaseModel):
    topic: Optional[str]
    title: str
    description: str
    icon: Optional[str]
    link: Optional[str]
```
