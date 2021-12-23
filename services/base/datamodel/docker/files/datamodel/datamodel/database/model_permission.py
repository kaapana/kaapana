import enum

from sqlalchemy import *
from sqlalchemy.orm import (scoped_session, sessionmaker, relationship,
                            backref)
from sqlalchemy.ext.declarative import declarative_base
from .base import Base

#Permission (role) should come from keycloak
# class Permission(enum.Enum):
#     READ = 0
#     WRITE = 1
#     DELETE = 2
##have many of it

class Access(Base):
    __tablename__ = 'access'
    id = Column(Integer, primary_key=True)
    group = Column(String(255))
    #permission = Column(Enum(Permission))


# class StudyAccess(Base):
#     # TODO=On what level to set access?
#     __tablename__ = 'studyaccess'
#     id = Column(Integer, primary_key=True)
#     access_id = Column(Integer, ForeignKey('access.id'))
#     access = relationship("Access", backref="studyaccess")
#     study_id = Column(Integer, ForeignKey('study.id'))
#     study = relationship("Study", backref="studyaccess")
#
# class FolderAccess(Base):
#     # TODO=On what level to set access?
#     __tablename__ = 'folderaccess'
#     id = Column(Integer, primary_key=True)
#     access_id = Column(Integer, ForeignKey('access.id'))
#     access = relationship("Access", backref="folderaccess")
#     folder_id = Column(Integer, ForeignKey('folder.id'))
#     folder = relationship("Folder", backref="folderaccess")