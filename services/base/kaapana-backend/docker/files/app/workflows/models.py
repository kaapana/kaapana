from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Table
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.schema import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type

from typing import List

from app.database import Base


# job_kaapana_instance_table = Table('job_kaapana_instance_table', Base.metadata,
#     Column('job_id', ForeignKey('job.id'), primary_key=True),
#     Column('kaapana_instance_id', ForeignKey('kaapana_instance.id'), primary_key=True)
# )
identifiers2dataset = Table(
    "identifier2dataset",
    Base.metadata,
    Column("identifier", ForeignKey("identifiers.id"), primary_key=True),
    Column("dataset", ForeignKey("dataset.name"), primary_key=True),
)


class Identifier(Base):
    __tablename__ = "identifiers"
    id = Column(String, primary_key=True)
    datasets = relationship(
        "Dataset", secondary=identifiers2dataset, back_populates="identifiers"
    )


class Dataset(Base):
    __tablename__ = "dataset"
    # id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True, primary_key=True)
    username = Column(String(64))
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    identifiers = relationship(
        "Identifier", secondary=identifiers2dataset, back_populates="datasets"
    )

    # many-to-one relationship
    kaapana_id = Column(Integer, ForeignKey("kaapana_instance.id"))
    kaapana_instance = relationship("KaapanaInstance", back_populates="datasets")


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
    encryption_key = Column(String(100), default="")
    allowed_dags = Column(mutable_json_type(dbtype=JSONB, nested=True), default={})
    allowed_datasets = Column(mutable_json_type(dbtype=JSONB, nested=True), default=[])
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    automatic_update = Column(Boolean(), default=False, index=True)
    automatic_workflow_execution = Column(Boolean(), default=False, index=True)

    # one-to-many relationships
    workflows = relationship(
        "Workflow", back_populates="kaapana_instance", cascade="all, delete"
    )
    jobs = relationship("Job", back_populates="kaapana_instance", cascade="all, delete")
    datasets = relationship(
        "Dataset", back_populates="kaapana_instance", cascade="all, delete"
    )
    # many-to-one relationships
    workflow_in_which_involved = Column(
        String(64), index=True
    )  # save information in string instead of sqlalchemy relationship - not ideal --> change it in future!

    # #https://stackoverflow.com/questions/5033547/sqlalchemy-cascade-delete
    # jobs = relationship("Job", back_populates="kaapana_instance", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("instance_name", "remote", name="_instance_name_remote"),
    )

    def __repr__(self):
        return "<KaapanaInstance {}://{}:{}>".format(
            self.protocol, self.host, self.port
        )


class Workflow(Base):
    __tablename__ = "workflow"
    workflow_id = Column(String(64), primary_key=True)
    workflow_name = Column(String(64))
    # dag_id of jobs which are summarized in that workflow (only makes sense for service workflows)
    dag_id = Column(String(64))
    # external_workflow_id = Column(Integer)
    username = Column(String(64))
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    automatic_execution = Column(Boolean(), default=False, index=True)
    service_workflow = Column(Boolean(), default=False, index=True)
    federated = Column(Boolean(), default=False, index=True)

    # many-to-one relationships
    kaapana_id = Column(Integer, ForeignKey("kaapana_instance.id"))
    kaapana_instance = relationship("KaapanaInstance", back_populates="workflows")
    # one-to-many relationships
    involved_kaapana_instances = Column(String(51200), default="[]", index=True)
    workflow_jobs = relationship(
        "Job", back_populates="workflow"
    )  # , cascade="all, delete")


class Job(Base):
    __tablename__ = "job"
    id = Column(Integer, primary_key=True)
    dag_id = Column(String(64))
    external_job_id = Column(Integer)
    owner_kaapana_instance_name = Column(String(64))
    conf_data = Column(mutable_json_type(dbtype=JSONB, nested=True))
    status = Column(String(64), index=True)
    run_id = Column(String(64), index=True)
    description = Column(String(1024), index=True)
    username = Column(String(64))
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    automatic_execution = Column(Boolean(), default=False, index=True)
    service_job = Column(Boolean(), default=False, index=True)

    # many-to-one relationships
    kaapana_id = Column(Integer, ForeignKey("kaapana_instance.id"))
    kaapana_instance = relationship("KaapanaInstance", back_populates="jobs")
    workflow_id = Column(String, ForeignKey("workflow.workflow_id"))
    workflow = relationship("Workflow", back_populates="workflow_jobs")

    # https://www.johbo.com/2016/creating-a-partial-unique-index-with-sqlalchemy-in-postgresql.html
    __table_args__ = (
        Index(
            "ix_kaapana_id_workflow_id_external_job_id",  # Index name
            "kaapana_id",
            "workflow_id",
            "external_job_id",  # Columns which are part of the index; extended with 'workflow_id'
            unique=True,
            postgresql_where=(external_job_id.isnot(None)),
        ),  # The condition
    )
