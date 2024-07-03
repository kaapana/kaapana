from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

Base = declarative_base()


class DicomData(Base):
    __tablename__ = "dicom_data"
    series_instance_uid = Column(String, primary_key=True)
    study_instance_uid = Column(String)

    description = Column(String)
    projects = relationship("Projects", secondary="data_projects")


# Data is bound to a project
class DataProjects(Base):
    __tablename__ = "data_projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    series_instance_uid = Column(String, ForeignKey("dicom_data.series_instance_uid"))
    project_id = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "series_instance_uid"),)
