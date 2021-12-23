from sqlalchemy import *
from sqlalchemy.orm import (relationship)
from .base import Base
from .type import DataType, StorageLocation
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB


class DicomPatient(Base):
    __tablename__ = 'dicom_patient'
    id = Column(Integer, primary_key=True)
    family_name = Column(String(255))
    given_name = Column(String(255))
    birthday = Column(DateTime, default=datetime.now())
    patient_uid = Column(String(255))
    dicom_studies = relationship("DicomStudy", back_populates="dicom_patient", cascade="all, delete-orphan")
    dataentity_id = Column(BigInteger, ForeignKey('dataentity.id'))
    data_entity = relationship("DataEntity", back_populates="dicom_patient", cascade="delete")
    meta = Column(JSONB)



class DicomStudy(Base):
    __tablename__ = 'dicom_study'
    id = Column(Integer, primary_key=True)
    study_uid = Column(String(255))
    patient_table_id = Column(Integer, ForeignKey('dicom_patient.id'))
    dicom_patient = relationship("DicomPatient", back_populates="dicom_studies")
    dicom_series = relationship("DicomSeries", back_populates="dicom_study", cascade="all, delete-orphan")
    study_description = Column(String(255))
    dataentity_id = Column(BigInteger, ForeignKey('dataentity.id'))
    data_entity = relationship("DataEntity", back_populates="dicom_study", cascade="delete", foreign_keys=dataentity_id)
    meta = Column(JSONB)


class DicomSeries(Base):
    __tablename__ = 'dicom_series'
    id = Column(Integer, primary_key=True)
    series_uid = Column(String(255))
    aet = Column(String(255))
    manufacturer = Column(String(255))
    seg_label = Column(String(255))
    body_part_examined = Column(String(255))
    series_description = Column(String(255))
    dicom_study_id = Column(Integer, ForeignKey('dicom_study.id'))
    dicom_study = relationship("DicomStudy", back_populates="dicom_series")
    dataentity_id = Column(BigInteger, ForeignKey('dataentity.id'))
    data_entity = relationship("DataEntity", back_populates="dicom_series", cascade="delete")
    dicom_instances = relationship("File", back_populates="dicom_series", cascade="delete", uselist=True)
    meta = Column(JSONB)
    __table_args__ = (Index('dicom_series_modality', meta['00080060 Modality_keyword']),
                      )
    # __table_args__ = (Index('index_jsondesc',
    #                   text("meta jsonb_path_ops"),
    #                   postgresql_using="gin"),)
    # Index(
    # 'my_index', id,
    # meta,
    # postgresql_ops={
    #     'data_lower': 'text_pattern_ops',
    #     'id': 'int4_ops'
    # })






