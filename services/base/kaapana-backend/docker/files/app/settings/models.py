import json
from typing import List

from app.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.types import JSON, VARCHAR, TypeDecorator


# TODO
# Following class throws error while migration, `app` not defined.
# This class is not properly loaded by migration script
# -----------------------------------------------------------------------------------------
# | File "/kaapana/app/alembic/versions/ff341e62afa9_migration.py", line 28, in upgrade   |
# |    sa.Column('value', app.workflows.models.JSONOrString(), nullable=True),            |
# | NameError: name 'app' is not defined                                                  |
# -----------------------------------------------------------------------------------------
class JSONOrString(TypeDecorator):
    impl = VARCHAR
    list_idntifier = "::list::"
    list_seperator = "|| ||"

    def process_bind_param(self, value, dialect):
        if isinstance(value, dict):
            return json.dumps(value)
        elif isinstance(value, list):
            return f"{self.list_seperator.join(value)}{self.list_idntifier}"
        return value

    def process_result_value(self, value, dialect):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            if isinstance(value, str) and value.endswith(self.list_idntifier):
                temp = value.replace(self.list_idntifier, "")
                value = temp.split(self.list_seperator)
            return value


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, Identity(start=1, cycle=True), primary_key=True)
    username = Column(String(64))
    instance_name = Column(String(64))
    key = Column(String(64))
    value = Column(JSONOrString)
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))

    # many-to-one relationships
    kaapana_instance_id = Column(Integer, ForeignKey("kaapana_instance.id"))
    kaapana_instance = relationship("KaapanaInstance", back_populates="settings")

    def __repr__(self):
        return f"Settings(id={self.id}, instance_name={self.instance_name}, username={self.username}, \
            key={self.username}, value={self.value}, updated={self.time_updated})"
