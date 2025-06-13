from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.schema import UniqueConstraint

Base = declarative_base()


class DataProjectMappings(Base):
    __tablename__ = "data_project_mappings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    series_instance_uid = Column(String)
    study_instance_uid = Column(String)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "series_instance_uid"),)
