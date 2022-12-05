from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint, Index

from app.database import Base


# job_kaapana_instance_table = Table('job_kaapana_instance_table', Base.metadata,
#     Column('job_id', ForeignKey('job.id'), primary_key=True),
#     Column('kaapana_instance_id', ForeignKey('kaapana_instance.id'), primary_key=True)
# )


class CohortIdentifier(Base):
    __tablename__ = "cohort_identifier"
    id = Column(Integer, index=True, primary_key=True)
    identifier_identifier = Column(String, ForeignKey('identifier.identifier'))
    cohort_name = Column(String, ForeignKey('cohort.cohort_name'))


class Identifier(Base):
    __tablename__ = "identifier"
    # id = Column(Integer, primary_key=True)
    identifier = Column(String(64), index=True, primary_key=True)
    cohorts = relationship("Cohort", secondary='cohort_identifier', back_populates="cohort_identifiers")


class Cohort(Base):
    __tablename__ = "cohort"
    # id = Column(Integer, primary_key=True)
    cohort_name = Column(String(64), index=True, primary_key=True)
    username = Column(String(64))
    cohort_query = Column(String(51200))
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    kaapana_id = Column(Integer, ForeignKey('kaapana_instance.id'))
    kaapana_instance = relationship("KaapanaInstance", back_populates="cohorts")
    cohort_identifiers = relationship("Identifier", secondary='cohort_identifier', back_populates="cohorts")


class Job(Base):
    __tablename__ = "job"
    id = Column(Integer, primary_key=True)
    dag_id = Column(String(64))
    external_job_id = Column(Integer)
    addressed_kaapana_instance_name = Column(String(64))
    conf_data = Column(String(51200))
    status = Column(String(64), index=True)
    run_id = Column(String(64), index=True)
    description = Column(String(1024), index=True)
    username = Column(String(64))
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    kaapana_id = Column(Integer, ForeignKey('kaapana_instance.id'))
    kaapana_instance = relationship("KaapanaInstance", back_populates="jobs")

    # https://www.johbo.com/2016/creating-a-partial-unique-index-with-sqlalchemy-in-postgresql.html
    __table_args__ = (
        Index(
            'ix_kaapana_id_external_job_id',  # Index name
            'kaapana_id', 'external_job_id',  # Columns which are part of the index
            unique=True,
            postgresql_where=(external_job_id.isnot(None))),  # The condition
    )


class KaapanaInstance(Base):
    __tablename__ = "kaapana_instance"
    id = Column(Integer, primary_key=True)
    instance_name = Column(String(64))
    token = Column(String(100))
    remote = Column(Boolean(), index=True)
    protocol = Column(String(64), index=True)
    host = Column(String(64), index=True)
    port = Column(Integer(), index=True)
    ssl_check = Column(Boolean(), index=True)
    fernet_key = Column(String(100))
    allowed_dags = Column(String(51200), default='[]')
    allowed_datasets = Column(String(2048), default='[]', index=True)
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    automatic_update = Column(Boolean(), default=False, index=True)
    automatic_job_execution = Column(Boolean(), default=False, index=True)
    jobs = relationship("Job", back_populates="kaapana_instance", cascade="all, delete")
    cohorts = relationship("Cohort", back_populates="kaapana_instance", cascade="all, delete")
    # #https://stackoverflow.com/questions/5033547/sqlalchemy-cascade-delete
    # jobs = relationship("Job", back_populates="kaapana_instance", passive_deletes=True)

    __table_args__ = (UniqueConstraint('instance_name', 'remote', name='_instance_name_remote'),)

    def __repr__(self):
        return '<KaapanaInstance {}://{}:{}>'.format(self.protocol, self.host, self.port)
