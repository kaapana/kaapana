from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Table
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.schema import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type

from typing import List

from app.database import Base


class Project(Base):
    __tablename__ = "projects"
    name = Column(String(32), primary_key=True)
    group_id = Column(String(37), unique=True)
    project_roles = Column(mutable_json_type(dbtype=JSONB, nested=True), default=[])
