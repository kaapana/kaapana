import enum
from sqlalchemy import *
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (scoped_session, sessionmaker, relationship,
                            backref)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from .base import Base
from .type import DataType, StorageLocation

class KaapanaNode(Base):
    __tablename__ = 'kaapanaNode'
    id = Column(Integer, primary_key=True)
    name = Column(String(30))

# class DataNode(Base):
#     __tablename__ = 'dataNode'
#     id = Column(Integer, primary_key=True)
#     name = Column(String(30))
#     kaapananode_id = Column(Integer, ForeignKey('kaapanaNode.id'))
#     kaapanaNode = relationship("KaapanaNode", back_populates="datanode")
#     dicom_patients = relationship("DicomPatient", back_populates="datanode", cascade="all, delete-orphan")
#     folders = relationship("Folder", back_populates="datanode", cascade="all, delete-orphan")

entity_access = Table('entity_access', Base.metadata,
                                 Column('dataentity_id', Integer, ForeignKey('dataentity.id')),
                                 Column('access_id', Integer, ForeignKey('access.id'))
                                 )
class DataEntity(Base):
    __tablename__ = 'dataentity'
    id = Column(BigInteger, primary_key=True)
    created = Column(DateTime, default=datetime.now())
    last_modified = Column(DateTime, default=datetime.now())
    meta_point = Column(JSONB)
    accesses = relationship("Access", secondary=entity_access)
    dataset = relationship("Dataset", back_populates="data_entity", foreign_keys="Dataset.dataentity_id")
    experiment = relationship("Experiment", back_populates="data_entity",
                              uselist=False, foreign_keys="[Experiment.dataentity_id]")
    file = relationship("File", back_populates="data_entity", uselist=False)
    dicom_patient = relationship("DicomPatient", back_populates="data_entity",  uselist=False)
    dicom_study = relationship("DicomStudy", back_populates="data_entity",  uselist=False)
    dicom_series = relationship("DicomSeries", back_populates="data_entity",
                                uselist=False, foreign_keys="DicomSeries.dataentity_id")
