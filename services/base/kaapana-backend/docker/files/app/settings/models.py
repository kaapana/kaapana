from app.database import Base
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    UniqueConstraint,
)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, Identity(start=1, cycle=True), primary_key=True)
    username = Column(String(64))
    instance_name = Column(String(64))
    key = Column(String(64))
    value = Column(JSON)
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))

    # store foreign key without relationship
    # relationship requires circular import which creates problem while running
    # create_kaapana_instance script
    kaapana_instance_id = Column(Integer, ForeignKey("kaapana_instance.id"))

    # Unique constraint for (username, instance_name, key)
    __table_args__ = (
        UniqueConstraint(
            "username", "instance_name", "key", name="uq_username_instance_key"
        ),
    )

    def __repr__(self):
        return f"Settings(id={self.id}, instance_name={self.instance_name}, username={self.username}, \
            key={self.username}, value={self.value}, updated={self.time_updated})"
