from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from config import (
    POSTGRES_USERNAME,
    POSTGRES_PASSWORD,
    POSTGRES_HOST,
    POSTGRES_PORT,
    DATABASE_NAME,
)

Base = declarative_base()


# Object tables
class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keycloak_id = Column(String, unique=True, nullable=False)
    projects = relationship("Projects", secondary="users_projects_roles")


class Projects(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    description = Column(String)
    data = relationship("Data", secondary="data_projects")
    users = relationship("Users", secondary="users_projects_roles")


class Roles(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String)
    name = Column(String)
    rights = relationship("Rights", secondary="roles_rights")


class Rights(Base):
    __tablename__ = "rights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String)
    claim_key = Column(String, nullable=False)
    claim_value = Column(String, nullable=False)
    roles = relationship("Roles", secondary="roles_rights")


class Data(Base):
    __tablename__ = "data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String)
    data_type = Column(String)
    projects = relationship("Projects", secondary="data_projects")
    dicom_series = relationship("DICOMSeries", uselist=False)


class DICOMSeries(Base):
    __tablename__ = "dicom_series"
    id = Column(Integer, primary_key=True, autoincrement=True)
    series_instance_uid = Column(String, unique=True, nullable=False)
    data_id = Column(Integer, ForeignKey("data.id"), unique=True)
    data = relationship("Data", uselist=False)


# Relationship tables


# Users are related to projects with a role
class UsersProjectsRoles(Base):
    __tablename__ = "users_projects_roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))


# Roles have a set of rights
class RolesRights(Base):
    __tablename__ = "roles_rights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    right_id = Column(Integer, ForeignKey("rights.id"))


# Data is bound to a project
class DataProjects(Base):
    __tablename__ = "data_projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_id = Column(Integer, ForeignKey("data.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))


engine = create_engine(
    f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{DATABASE_NAME}"
)

Base.metadata.create_all(engine)

# TODO: Prepared statements
# TODO: Indexes
# TODO: Seperation of concerns
# TODO: Concept: Partitioning (Maybe creation date)
# TODO: Hashing and Cache
