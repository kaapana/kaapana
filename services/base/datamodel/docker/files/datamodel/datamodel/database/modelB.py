import enum
from sqlalchemy import *
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (scoped_session, sessionmaker, relationship,
                            backref)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from .base import Base
from .type import DataType, StorageLocation

class DataEntityB(Base):
    __tablename__ = 'dataentityb'
    id = Column(BigInteger, primary_key=True)
    meta = Column(JSONB)
    type = Column(String(255))
    collection = relationship("Collection", back_populates="data_entityb", foreign_keys="Collection.dataentityb_id")
    link_source = relationship("Link", back_populates="source", foreign_keys="Link.source_id")
    link_target = relationship("Link", back_populates="target", foreign_keys="Link.target_id")

Collection2DataEntity = Table('Collection2DataEntity', Base.metadata,
                                 Column('foreign_entity_id', BigInteger, ForeignKey('dataentityb.id')),
                                 Column('collection_id', Integer, ForeignKey('collection.id'))
                                 )

class Collection(Base):
    __tablename__ = 'collection'
    id = Column(Integer, primary_key=True)
    collection_2_dataentity = relationship("DataEntityB", secondary=Collection2DataEntity)
    dataentityb_id = Column(BigInteger, ForeignKey("dataentityb.id"))
    data_entityb = relationship("DataEntityB", back_populates="collection", cascade="delete", foreign_keys=dataentityb_id)
    type = Column(String(255))

class Link(Base):
    __tablename__ = 'link'
    id = Column(Integer, primary_key=True)
    type = Column(String(255))
    meta = Column(JSONB)
    source_id = Column(BigInteger, ForeignKey("dataentityb.id"))
    source = relationship("DataEntityB", back_populates="link_source", cascade="delete", foreign_keys=source_id)
    target_id = Column(BigInteger, ForeignKey("dataentityb.id"))
    target = relationship("DataEntityB", back_populates="link_target", cascade="delete", foreign_keys=target_id)