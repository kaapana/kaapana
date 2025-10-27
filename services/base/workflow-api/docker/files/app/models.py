from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.schemas import TaskRunStatus, WorkflowRunStatus
from sqlalchemy import Column, DateTime
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

    id = Column(Integer, primary_key=True, index=True)
    workflow_engine = Column(String)
    title = Column(String, index=True)
    version = Column(Integer)
    definition = Column(String)
    config_definition = Column(JSONB)  # Schema for validate workflow run config
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

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

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    config_definition = Column(JSONB)
    lifecycle_status: Mapped[WorkflowRunStatus] = mapped_column(
        SqlEnum(WorkflowRunStatus), default=WorkflowRunStatus.CREATED, nullable=False
    )
    labels: Mapped[list["Label"]] = relationship(
        "Label",
        secondary=workflowrun_label,
        back_populates="workflow_runs",
        lazy="selectin",  # by default lazy='select', which means that the related items are loaded only when they are accessed
    )
    external_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
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
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String)
    value = Column(String)
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

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    title = Column(String, index=True)  # e.g. total_segmentator_0
    display_name = Column(String)
    type = Column(String)  # e.g. TotalSegmentatorOperator
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

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    downstream_task_id = Column(Integer, ForeignKey("tasks.id"))

    task = relationship(
        "Task", foreign_keys=[task_id], back_populates="downstream_tasks"
    )
    downstream_task = relationship("Task", foreign_keys=[downstream_task_id])
    __table_args__ = (UniqueConstraint("task_id", "downstream_task_id"),)


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"))
    external_id = Column(String, nullable=True)
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
