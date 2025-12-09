from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.schemas import TaskRunStatus, WorkflowRunStatus
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


workflow_label = Table(
    "workflow_label",
    Base.metadata,
    Column("workflow_id", ForeignKey("workflows.id"), primary_key=True),
    Column("label_id", ForeignKey("labels.id"), primary_key=True),
)

# Association table for WorkflowRun <-> Label
workflowrun_label = Table(
    "workflowrun_label",
    Base.metadata,
    Column("workflowrun_id", ForeignKey("workflow_runs.id"), primary_key=True),
    Column("label_id", ForeignKey("labels.id"), primary_key=True),
)


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("title", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_engine: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer)
    definition: Mapped[str] = mapped_column(String)
    workflow_parameters: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    removed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    runs: Mapped[List[WorkflowRun]] = relationship(
        "WorkflowRun", back_populates="workflow"
    )

    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="workflow", cascade="save-update, merge"
    )  # NOTE: only update operations cascade, deletes don’t. Task might be related to historical workflow runs

    labels: Mapped[list["Label"]] = relationship(
        "Label", secondary=workflow_label, back_populates="workflows", lazy="selectin"
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(Integer, ForeignKey("workflows.id"))
    workflow_parameters: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    lifecycle_status: Mapped[WorkflowRunStatus] = mapped_column(
        SqlEnum(WorkflowRunStatus), default=WorkflowRunStatus.CREATED, nullable=False
    )
    labels: Mapped[list["Label"]] = relationship(
        "Label",
        secondary=workflowrun_label,
        back_populates="workflow_runs",
        lazy="selectin",
    )
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="runs", lazy="selectin"
    )
    task_runs: Mapped[List["TaskRun"]] = relationship(
        "TaskRun", back_populates="workflow_run", lazy="selectin"
    )


class Label(Base):
    __tablename__ = "labels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    __table_args__ = (UniqueConstraint("key", "value"),)

    # reverse relationships
    workflows: Mapped[list[Workflow]] = relationship(
        "Workflow",
        secondary=workflow_label,
        back_populates="labels",
    )

    workflow_runs: Mapped[list[WorkflowRun]] = relationship(
        "WorkflowRun",
        secondary=workflowrun_label,
        back_populates="labels",
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(Integer, ForeignKey("workflows.id"))
    title: Mapped[str] = mapped_column(String, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String)
    downstream_tasks: Mapped[List["DownstreamTask"]] = relationship(
        "DownstreamTask",
        back_populates="task",
        cascade="all, delete-orphan",
        foreign_keys="DownstreamTask.task_id",
    )

    workflow: Mapped["Workflow"] = relationship(
        "Workflow", back_populates="tasks"
    )  # many-to-one
    task_runs: Mapped[List["TaskRun"]] = relationship(
        "TaskRun",
        back_populates="task",
    )  # one-to-many


class DownstreamTask(Base):
    __tablename__ = "downstream_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"))
    downstream_task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"))

    task = relationship(
        "Task", foreign_keys=[task_id], back_populates="downstream_tasks"
    )
    downstream_task = relationship("Task", foreign_keys=[downstream_task_id])
    __table_args__ = (UniqueConstraint("task_id", "downstream_task_id"),)


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"))
    workflow_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_runs.id")
    )
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lifecycle_status: Mapped[TaskRunStatus] = mapped_column(
        SqlEnum(TaskRunStatus), default=TaskRunStatus.CREATED, nullable=False
    )

    task: Mapped["Task"] = relationship(
        "Task", back_populates="task_runs", lazy="selectin"
    )
    workflow_run: Mapped["WorkflowRun"] = relationship(
        "WorkflowRun", back_populates="task_runs"
    )

    @property
    def task_title(self) -> str | None:
        """Expose the related Task.title as an attribute for serializers (read-only).

        This keeps the DB normalized (no denormalized task_title column) while
        allowing Pydantic's from_attributes=True to read `task_title` without
        changing schemas. Ensure queries eager-load `.task` to avoid lazy IO.
        """
        task = getattr(self, "task", None)
        return task.title if task is not None else None
