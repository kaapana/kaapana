from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class NotificationBase(BaseModel):
    topic: str | None = Field(
        None,
        description="Used as heading for grouping notifications",
        examples=["Workflow 123"],
    )
    title: str = Field(
        ...,
        description="A heading for the notification",
        examples=["Workflow completed"],
    )
    description: str = Field(
        ...,
        description="HTML encoded content of the notifcation",
        examples=[
            "<b>Successs</b> workflow <em>123</em> finished successful.",
            "Hello World!",
        ],
    )
    icon: str | None = Field(
        None,
        description="A vuetify supported icon identifier (e.g material design icons)",
        examples=["mdi-information"],
    )
    link: str | None = Field(
        None,
        description="Platform internal link, guiding the user to the source of the notificaiton.",
        examples=["/flow/dags/collect-metadata/grid?tab=details&task_id=dcm2json"],
    )


class Notification(NotificationBase):
    id: UUID
    timestamp: datetime = Field(
        ..., desciption="Timestamp when notification was created"
    )
    receivers: list[str] = Field(
        ..., desciption="IDs of the users receiving this notification"
    )
    receviers_read: dict[str, datetime | None] = Field(
        ..., desciption="Receiver IDs mapped to reading timestamps"
    )


class NotificationUser(NotificationBase):
    id: UUID
    timestamp: datetime = Field(
        ..., desciption="Timestamp when notification was created"
    )


class NotificationCreate(NotificationBase):
    receivers: list[str] = Field(
        ..., desciption="IDs of the users receiving this notification"
    )


class NotificationCreateNoReceivers(NotificationBase): ...
