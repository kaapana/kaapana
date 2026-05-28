import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class ExtensionStatus(enum.StrEnum):
    PENDING = "pending"
    PULLING = "pulling"
    PULLING_FAILED = "pulling_failed"
    INSTALLING = "installing"
    INSTALLATION_FAILED = "installing_failed"
    INSTALLED = "installed"
    UNINSTALLING = "uninstalling"
    UNINSTALLED = "uninstalled"
    UNINSTALLING_FAILED = "uninstalling_failed"


class RegisteredRepository(Base):
    __tablename__ = "registries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    repository_url: Mapped[str] = mapped_column(
        String(2048), nullable=False, unique=False
    )

    authentication: Mapped[str] = mapped_column(String(2048), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    extensions: Mapped[list["Extension"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )


class Extension(Base):
    __tablename__ = "extensions"
    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "tag",
            name="uq_repository_id_tag",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("registries.id", ondelete="CASCADE"),
        nullable=False,
    )

    ### REGEX: [a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}
    ### Corresponds to <reference> or tag of a manifest in the OCI distribution spec
    tag: Mapped[str] = mapped_column(String(128), nullable=False)

    manifest: Mapped[JSON] = mapped_column(JSON, nullable=False)

    status: Mapped[ExtensionStatus] = mapped_column(
        Enum(
            ExtensionStatus,
            name="extension_status",
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
        ),
        nullable=False,
        default=ExtensionStatus.PENDING,
        server_default=ExtensionStatus.PENDING.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    repository: Mapped[RegisteredRepository] = relationship(back_populates="extensions")

    contents: Mapped[list["Content"]] = relationship(
        back_populates="extension",
        cascade="all, delete-orphan",
    )


class ContentStatus(enum.StrEnum):
    PENDING = "pending"
    INSTALLING = "installing"
    INSTALLATION_FAILED = "installation_failed"
    INSTALLED = "installed"
    UNINSTALLING = "uninstalling"
    UNINSTALLATION_FAILED = "uninstallation_failed"
    UNINSTALLED = "uninstalled"


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)

    status: Mapped[ContentStatus] = mapped_column(
        Enum(
            ContentStatus,
            name="content_status",
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
        ),
        nullable=False,
        default=ContentStatus.PENDING,
        server_default=ContentStatus.PENDING.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    extension: Mapped[Extension] = relationship(back_populates="contents")


ALLOWED_EXTENSION_STATUS_TRANSITIONS = {
    ExtensionStatus.PENDING: [ExtensionStatus.PULLING, ExtensionStatus.UNINSTALLING],
    ExtensionStatus.PULLING: [
        ExtensionStatus.PULLING_FAILED,
        ExtensionStatus.INSTALLING,
        ExtensionStatus.UNINSTALLING,
    ],
    ExtensionStatus.INSTALLING: [
        ExtensionStatus.INSTALLATION_FAILED,
        ExtensionStatus.INSTALLED,
        ExtensionStatus.UNINSTALLING,
    ],
    ExtensionStatus.INSTALLED: [
        ExtensionStatus.UNINSTALLING,
    ],
    ExtensionStatus.UNINSTALLING: [
        ExtensionStatus.UNINSTALLED,
        ExtensionStatus.UNINSTALLING_FAILED,
        ExtensionStatus.UNINSTALLING,
    ],
    ExtensionStatus.UNINSTALLED: [],
    ### ERROR STATES ###
    ExtensionStatus.PULLING_FAILED: [
        ExtensionStatus.PENDING,
        ExtensionStatus.UNINSTALLING,
    ],
    ExtensionStatus.INSTALLATION_FAILED: [
        ExtensionStatus.PENDING,
        ExtensionStatus.UNINSTALLING,
    ],
    ExtensionStatus.UNINSTALLING_FAILED: [
        ExtensionStatus.UNINSTALLING,
    ],
}


ALLOWED_CONTENT_STATUS_TRANSITIONS = {
    ContentStatus.PENDING: [
        ContentStatus.INSTALLING,
        ContentStatus.UNINSTALLING,
    ],
    ContentStatus.INSTALLING: [
        ContentStatus.INSTALLATION_FAILED,
        ContentStatus.INSTALLED,
        ContentStatus.UNINSTALLING,
    ],
    ContentStatus.INSTALLED: [
        ContentStatus.UNINSTALLING,
    ],
    ContentStatus.UNINSTALLING: [
        ContentStatus.UNINSTALLED,
        ContentStatus.UNINSTALLATION_FAILED,
    ],
    ContentStatus.UNINSTALLED: [],
    ### ERROR STATES ###
    ContentStatus.INSTALLATION_FAILED: [
        ContentStatus.INSTALLING,
        ContentStatus.UNINSTALLING,
    ],
    ContentStatus.UNINSTALLATION_FAILED: [
        ContentStatus.UNINSTALLING,
    ],
}
