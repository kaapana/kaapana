.. _services:

Kaapana Services
================

You can access Kaapana services in processing containers:

- **dicom-web-filter**: Access control to dicom files (PACS)
- **access-information-interface**: Manage users, roles, rights, software and other access control data.
- **notifications**: Manage user or project notifications
- **minio**: Manage files in the persistent object store

There is a ``kaapanapy`` library package that should allow you to easily use these services.

Notification Service
--------------------

You can send notifications to the user (yourself) or to the project within your authorization scope (project users)
using the following commands.

You can also find an example in:

``templates_and_examples/examples/processing-pipelines/example/processing-containers/notify/files/example-notify.py``

Example usage:

.. code-block:: python

    from kaapanapy.services import NotificationService

    NotificationService.post_notification_to_user(
        user_id: str, project_id: str, notification: Notification
    )

    NotificationService.post_notification_to_project(
        project_id: str, notification: Notification
    )

Notification Model
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    class Notification(BaseModel):
        topic: Optional[str]
        title: str
        description: str
        icon: Optional[str]
        link: Optional[str]
