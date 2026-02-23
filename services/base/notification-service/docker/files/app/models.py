import uuid
import datetime
from sqlalchemy import Column, UUID, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import String, ARRAY, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func


class Base(DeclarativeBase): ...


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("array_ndims(receivers) = 1", name="receivers_one_dimensional"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    topic: Mapped[str | None] = Column(String, nullable=True)
    title: Mapped[str] = Column(String)
    description: Mapped[str] = Column(String)
    icon: Mapped[str | None] = Column(String, nullable=True)
    link: Mapped[str | None] = Column(String, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    receivers: Mapped[list[str]] = Column(ARRAY(String))
    receviers_read: Mapped[dict[str, datetime.datetime | None]] = Column(
        JSONB, default=dict
    )
