from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.schema import UniqueConstraint

Base = declarative_base()


class Projects(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String)
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


class Data(
    Base
):  # TODO: Actually we lied, this is not generic and just DICOM data specific
    __tablename__ = "data"
    id = Column(
        Integer, primary_key=True, autoincrement=True
    )  # For faster querying (Int vs String)
    description = Column(String)
    data_type = Column(String)
    series_instance_uid = Column(String, nullable=False, unique=True)
    study_instance_uid = Column(String)
    projects = relationship("Projects", secondary="data_projects")


# Relationship tables


# Users are related to projects with a role
class UsersProjectsRoles(Base):
    __tablename__ = "users_projects_roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    keycloak_id = Column(String(length=36), nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "role_id", "keycloak_id"),)


# Roles have a set of rights
class RolesRights(Base):
    __tablename__ = "roles_rights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    right_id = Column(Integer, ForeignKey("rights.id"))
    __table_args__ = (UniqueConstraint("role_id", "right_id"),)


# Data is bound to a project
class DataProjects(Base):
    __tablename__ = "data_projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_id = Column(Integer, ForeignKey("data.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    __table_args__ = (UniqueConstraint("project_id", "data_id"),)


### TODO We might need indices to avoid duplicated rows in the relationship tables
