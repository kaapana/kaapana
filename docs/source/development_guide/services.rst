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

.. _notification_service:

You can send notifications to the user (yourself) or to the project within your authorization scope (project users)
using the following commands.

You can also find an example in:

``templates_and_examples/examples/processing-pipelines/example/processing-containers/notify/files/example-notify.py``

Example usage:

.. code-block:: python

    from kaapanapy.services import Notification, NotificationService

    NotificationService.send(
        project_id: str, user_id: str, notification: Notification
    )

    NotificationService.send(
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

It is possible to send notification on failure of the workflow. 
Be aware that workflows with Single Execution flag will send notification for each failed job.
You can set it up for the dag by adding it to the DAG arguments:

.. code-block:: python

    args = {
        "ui_forms": ui_forms,
        "ui_visible": True,
        "owner": "kaapana",
        "start_date": days_ago(0),
        "retries": 1,
        "retry_delay": timedelta(seconds=30),
        "send_notification_on_workflow_failure" : True
    }

    dag = DAG(
        dag_id="collect-metadata",
        default_args=args,
        concurrency=50,
        max_active_runs=50,
        schedule_interval=None,
    )