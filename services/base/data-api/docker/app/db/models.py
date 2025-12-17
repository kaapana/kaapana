from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DataEntityORM(Base):
    __tablename__ = "data_entities"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("data_entities.id", ondelete="SET NULL"), nullable=True, index=True
    )

    storage_coordinates: Mapped[list[StorageCoordinateORM]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    metadata_entries: Mapped[list[MetadataEntryORM]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    parent: Mapped["DataEntityORM | None"] = relationship(
        "DataEntityORM",
        remote_side="DataEntityORM.id",
        back_populates="children",
        foreign_keys="DataEntityORM.parent_id",
    )
    children: Mapped[list["DataEntityORM"]] = relationship(
        "DataEntityORM",
        back_populates="parent",
    )


class StorageCoordinateORM(Base):
    __tablename__ = "storage_coordinates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("data_entities.id", ondelete="CASCADE"),
        index=True,
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Store type-specific details as JSON so we don't overfit the schema early.
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    entity: Mapped[DataEntityORM] = relationship(back_populates="storage_coordinates")


class MetadataEntryORM(Base):
    __tablename__ = "metadata_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("data_entities.id", ondelete="CASCADE"),
        index=True,
    )

    key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    entity: Mapped[DataEntityORM] = relationship(back_populates="metadata_entries")
    artifacts: Mapped[list[ArtifactORM]] = relationship(
        back_populates="metadata_entry",
        cascade="all, delete-orphan",
    )


class ArtifactORM(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metadata_entry_id: Mapped[int] = mapped_column(
        ForeignKey("metadata_entries.id", ondelete="CASCADE"),
        index=True,
    )

    artifact_id: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    metadata_entry: Mapped[MetadataEntryORM] = relationship(back_populates="artifacts")


class MetadataSchemaORM(Base):
    __tablename__ = "metadata_schemas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
