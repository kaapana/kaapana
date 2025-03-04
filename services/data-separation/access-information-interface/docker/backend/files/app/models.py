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
    kubernetes_namespace = Column(String, unique=True)
    s3_bucket = Column(String, unique=True)
    opensearch_index = Column(String, unique=True)


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


# Software is bound to a project
class SoftwareMappings(Base):
    __tablename__ = "software_mappings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # software_uuid = Column(Integer, ForeignKey("software.id"))
    software_uuid = Column(String(length=72), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    __table_args__ = (UniqueConstraint("project_id", "software_uuid"),)


### TODO We might need indices to avoid duplicated rows in the relationship tables
