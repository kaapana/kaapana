from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from config import POSTGRES_USERNAME, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, DATABASE_NAME

Base = declarative_base()

# Object tables
class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    keycloak_id = Column(String)
    projects = relationship('Projects', secondary='users_projects_roles')

class Projects(Base):
    __tablename__ = 'projects'
    id = Column(Integer, Sequence('project_id_seq'), primary_key=True)
    name = Column(String)
    description = Column(String)
    data = relationship('Data', secondary='data_projects') 
    users = relationship('Users', secondary='users_projects_roles') 

class Roles(Base):
    __tablename__ = 'roles'
    id = Column(Integer, Sequence('role_id_seq'), primary_key=True)
    description = Column(String)
    name = Column(String)
    rights = relationship('Rights', secondary='roles_rights')

class Rights(Base):
    __tablename__ = 'rights'
    id = Column(Integer, Sequence('right_id_seq'), primary_key=True)
    description = Column(String)
    claim_key = Column(String)
    claim_value = Column(String)
    roles = relationship('Roles', secondary='roles_rights')

class Data(Base):
    __tablename__ = 'data'
    id = Column(Integer, Sequence('data_id_seq'), primary_key=True)
    description = Column(String)
    data_type = Column(String)
    projects = relationship('Projects', secondary='data_projects')
    dicom_series = relationship('DICOMSeries', uselist=False)

class DICOMSeries(Base):
    __tablename__ = 'dicom_series'
    series_instance_uid = Column(String, primary_key=True)
    data_id = Column(Integer, ForeignKey('data.id'), unique=True)
    data = relationship('Data', uselist=False)

# Relationship tables

# Users are related to projects with a role
class UsersProjectsRoles(Base):
    __tablename__ = 'users_projects_roles'
    id = Column(Integer, Sequence('user_project_role_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    role_id = Column(Integer, ForeignKey('roles.id'))

# Roles have a set of rights
class RolesRights(Base):
    __tablename__ = 'roles_rights'
    id = Column(Integer, Sequence('role_right_id_seq'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    right_id = Column(Integer, ForeignKey('rights.id'))

# Data is bound to a project
class DataProjects(Base):
    __tablename__ = 'data_projects'
    id = Column(Integer, Sequence('data_project_id_seq'), primary_key=True)
    data_id = Column(Integer, ForeignKey('data.id'))
    project_id = Column(Integer, ForeignKey('projects.id'))


engine = create_engine(f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{DATABASE_NAME}")

Base.metadata.create_all(engine)