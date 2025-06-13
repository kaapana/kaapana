from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DataProjectMappings(OrmBaseModel):
    series_instance_uid: str
    study_instance_uid: str
    project_id: UUID
