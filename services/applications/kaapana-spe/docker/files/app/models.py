from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Table
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.schema import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy_json import mutable_json_type

from typing import List

from database import Base

class Dataset(Base):
    __tablename__ = "dataset"

    name = Column(String(64), index=True, primary_key=True) # TODO looks like uuid string, why not actual UUID object?
    username = Column(String(64))
    time_created = Column(DateTime(timezone=True))
    time_updated = Column(DateTime(timezone=True))
    identifiers = relationship(
        "Identifier", secondary=identifiers2dataset, back_populates="datasets"
    )
    implicit_generation = Column(Boolean, nullable=True)

    # many-to-one relationship
    kaapana_id = Column(Integer, ForeignKey("kaapana_instance.id"))
    kaapana_instance = relationship("KaapanaInstance", back_populates="datasets")


class DatasetSpecification(Base):
    __tablename__ = "dataset_specification"

    id = Column(UUID, primary_key=True) # TODO: Some people say using uuids as primary key is bad practice. Not sure why atm. # TODO: unique UUID, can be used to identify a specification across the federation. 
    description = Column(String, nullable=True)
    managing_site = Column(UUID)
    created_on = Column(DateTime)
    modifled_on = Column(DateTime)
    implicit_generation = Column(Boolean, nullable=True)

    # TODO check up with lorenz (and Benjamin) on those, also consult data seperation protocol:
    # access_policy:access_type
    # access_policy:allowed_clients
    # access_policy:restriction
    
    # TODO Foreign key?
    # contact:email
    # contact:first_name
    # contact:lastname

class Contribution(Base):
    __tablename__ = "contribution"

    id = Column(UUID, primary_key=True) # TODO: s.o.
    created_on = Column(DateTime)
    modifled_on = Column(DateTime)
    implicit_generation = Column(Boolean, nullable=True)

    
    # access_policy:access_type
    # Proposal: There seem to be more than one kind of access type: 
    #   1. Organizational access type: Sounds more like license agreements, aka if you use this data you aggree to use it only in a specific way.
    #   2. Technical access type: If the user is actually able to access the data.
    # => Is there some middle ground? Should it be the responsibility to enforce the user to use the data only in the way specified 
    # access_policy:allowed_clients
    # access_policy:restriction
    
    # TODO clarify: just Foreign_key(contact.id)?
    contact_mail = Column(String, ForeignKey(contact.email))
    contact_first_name = Column(String, ForeignKey(contact.first_name))
    contact_last_name = Column(String, ForeignKey(contact.last_name))



class Application(Base):
    __tablename__ = "application"

    id = Column(Integer, primary_key=True)
    time_created = Column(DateTime)
    time_answered = Column(DateTime, nullable=True)
    answer = Column(Boolean, nullable=True) # TODO maybe foreign key with answer:enum[allow|deny|request_refinement], answer:refinement_required
    
    applicant = Column(String)
    dataset_reference = Column(UUID, ForeignKey("dataset.id")) # TODO check correct spelling of database table
    dataset_specification_reference = Column(UUID, ForeignKey(dataset_specification.id))
    
    project_reference_id = Column(String, nullable=True)
    project_description = Column(String, nullable=True)

class SPEInstance(Base):
    __tablename__ = "spe_instance"

    id = Column(Integer)
    time_created = Column(DateTime)
    time_last_accessed = Column(DateTime)
    state = Column(Boolean) # TODO not sure if this is good to store in a database. maybe the frontend should just ping to check in a responsive way.
    access_url = Column(String) # TODO maybe this already exists somewhere and can just be filtered by the endpoint.
    
