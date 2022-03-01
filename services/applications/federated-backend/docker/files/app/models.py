from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Table
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# job_kaapana_instance_table = Table('job_kaapana_instance_table', Base.metadata,
#     Column('job_id', ForeignKey('job.id'), primary_key=True),
#     Column('kaapana_instance_id', ForeignKey('kaapana_instance.id'), primary_key=True)
# )

class Job(Base):
    __tablename__ = "job"
    id = Column(Integer, primary_key=True)
    dag_id = Column(String(64))
    external_job_id = Column(Integer)
    addressed_kaapana_node_id = Column(String(64))
    job_data = Column(String(10240), index=True)
    conf_data = Column(String(51200), index=True)
    local_data = Column(String(10240), index=True)
    dry_run = Column(Boolean(), index=True)
    status = Column(String(64), index=True)
    run_id = Column(String(64), index=True)
    description = Column(String(256), index=True)
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    kaapana_id = Column(Integer, ForeignKey('kaapana_instance.id'))
    kaapana_instance = relationship("KaapanaInstance", back_populates="jobs")

class KaapanaInstance(Base):
    __tablename__ = "kaapana_instance"
    id = Column(Integer, primary_key=True)
    node_id = Column(String(64))
    token = Column(String(100))
    remote = Column(Boolean(), index=True)
    protocol = Column(String(64), index=True)
    host = Column(String(64), index=True)
    port = Column(Integer(), index=True)
    ssl_check = Column(Boolean(), index=True)
    fernet_key = Column(String(100))
    allowed_dags = Column(String(51200), default='[]', index=True)
    allowed_datasets = Column(String(1024),  default='[]', index=True)
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    automatic_update = Column(Boolean(), default=False, index=True)
    automatic_job_execution = Column(Boolean(), default=False, index=True)
    jobs = relationship("Job", back_populates="kaapana_instance", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('node_id', 'remote', name='_node_id_remote'),)

    def __repr__(self):
        return '<KaapanaInstance {}://{}:{}>'.format(self.protocol, self.host, self.port)
