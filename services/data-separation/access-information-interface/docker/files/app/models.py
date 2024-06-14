from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()


class Projects(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    description = Column(String)
    data = relationship("Data", secondary="data_projects")


class Roles(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String)
    name = Column(String, unique=True)
    rights = relationship("Rights", secondary="roles_rights")


class Rights(Base):
    __tablename__ = "rights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String)
    name = Column(String, unique=True)
    claim_key = Column(String, nullable=False)
    claim_value = Column(String, nullable=False)
    roles = relationship("Roles", secondary="roles_rights")


class Data(Base):
    __tablename__ = "data"
    id = Column(
        Integer, primary_key=True, autoincrement=True
    )  # For faster querying (Int vs String)
    description = Column(String)
    data_type = Column(String)
    data_storage_id = Column(
        String, nullable=False, unique=True
    )  # In case of DICOM data, this is the SeriesInstanceUID
    projects = relationship("Projects", secondary="data_projects")


# Relationship tables


# Users are related to projects with a role
class UsersProjectsRoles(Base):
    __tablename__ = "users_projects_roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    keycloak_id = Column(String(length=36), nullable=False)


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


### TODO We might need indices to avoid duplicated rows in the relationship tables
