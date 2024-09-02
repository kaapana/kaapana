import datetime
from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy_json import NestedMutableDict, NestedMutableList
from typing_extensions import Self


class SettingsBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    key: Optional[str] = None
    value: Optional[Union[NestedMutableDict, Any]] = ...

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, v: Union[NestedMutableDict, Any]):
        try:
            value = NestedMutableDict(v)
            return value
        except (TypeError, ValueError):
            return v


class Settings(SettingsBase):
    id: int
    kaapana_instance_id: int
    username: Optional[str] = None
    time_created: datetime.datetime
    time_updated: datetime.datetime

    @field_validator("time_created", "time_updated")
    @classmethod
    def convert_time_created(cls, v):
        if isinstance(v, datetime.datetime):
            return v
        else:
            return datetime.datetime.timestamp(v)

    # @field_validator("time_updated", mode="before")
