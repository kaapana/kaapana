from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type

from typing import List

from app.database import Base


class AccessListEntree(Base):
    __tablename__ = "accesslistentree"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String(37))
    permissions = Column(String(3))
    accesstable_primary_key = Column(
        String(32), ForeignKey("accesstable.object_primary_key")
    )
    accesstable = relationship(
        "AccessTable", back_populates="accesslistentree", cascade="all, delete"
    )


class AccessTable(Base):
    __tablename__ = "accesstable"
    object_primary_key = Column(String(32), primary_key=True)
    accesslistentree = relationship(
        "AccessListEntree", back_populates="accesstable", cascade="all, delete"
    )


class Project(Base):
    __tablename__ = "projects"
    name = Column(String(32), primary_key=True)
    group_id = Column(String(37), unique=True)
    project_roles = Column(mutable_json_type(dbtype=JSONB, nested=True), default=[])
    accesstable_primary_key = Column(
        String(32), ForeignKey("accesstable.object_primary_key")
    )
