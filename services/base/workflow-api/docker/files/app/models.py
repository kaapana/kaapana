import json
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON 
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
from .schemas import LifecycleStatus


class Base(AsyncAttrs, DeclarativeBase):
    pass

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True)
    version = Column(Integer)
    definition = Column(String)
    config_definition = Column(JSONB)
    creation_time = Column(DateTime, default=datetime.utcnow)
    # User separation
    project_id = Column(UUID(as_uuid=True), nullable=False)
    username = Column(String(64))

    runs = relationship("WorkflowRun", back_populates="workflow")
    tasks = relationship("Task", back_populates="workflow")
    ui_schema = relationship("WorkflowUISchema", back_populates="workflow", uselist=False)

    #ui_schema_id = Column(Integer, ForeignKey("workflow_ui_schemas.id"), nullable=True)

class WorkflowUISchema(Base):
    __tablename__ = "workflow_ui_schemas"

    id = Column(Integer, primary_key=True, index=True)
    schema_definition = Column(JSONB)
    # FK to a specific workflow (which includes identifier + version)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, unique=True)

    workflow = relationship("Workflow", back_populates="ui_schema")

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    config = Column(JSONB)
    creation_time = Column(DateTime, default=datetime.utcnow)
    lifecycle_status = Column(SqlEnum(LifecycleStatus), default=LifecycleStatus.PENDING, nullable=False)
    labels = Column(JSONB) # Key-Value pairs for labeling

    celery_task_id = Column(String, nullable=True) # Celery task ID for tracking

    external_id = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    workflow = relationship("Workflow", back_populates="runs")
    task_runs = relationship("TaskRun", back_populates="workflow_run")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    task_identifier = Column(String, index=True) # e.g. total_segmentator_0
    display_name = Column(String)
    type = Column(String) # e.g. TotalSegmentatorOperator
    input_tasks_ids = Column(JSONB) # Optional: List of Task IDs
    output_tasks_ids = Column(JSONB) # Optional: List of Task IDs

    workflow = relationship("Workflow", back_populates="tasks")
    task_runs = relationship("TaskRun", back_populates="task")

class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"))
    lifecycle_status = Column(SqlEnum(LifecycleStatus), default=LifecycleStatus.PENDING, nullable=False)

    task = relationship("Task", back_populates="task_runs")
    workflow_run = relationship("WorkflowRun", back_populates="task_runs")

