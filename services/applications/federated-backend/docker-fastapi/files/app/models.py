from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .database import Base
# class User(Base):
#     __tablename__ = "users"

#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String, index=True)
#     hashed_password = Column(String)
#     is_active = Column(Boolean, default=True)

#     items = relationship("Item", back_populates="owner")

# class Jobs(Base):
#     __tablename__ = "jobs"
#     id = Column(Integer, primary_key=True)
#     conf = Column(String(1024), index=True)
#     dry_run = Column(Boolean(), index=True)

class ClientNetwork(Base):
    __tablename__ = "client_network"
    id = Column(Integer, primary_key=True)
    token = Column(String(100))
    protocol = Column(String(64), index=True)
    host = Column(String(64), index=True, unique=True)
    port = Column(Integer(), index=True)
    ssl_check = Column(Boolean(), index=True)
    fernet_key = Column(String(100))
    allowed_dags = Column(String(1024), index=True)
    allowed_datasets = Column(String(1024), index=True)
    automatic_update = Column(Boolean(), index=True)
    automatic_job_execution = Column(Boolean(), index=True)

    def __repr__(self):
        return '<ClientNetwork {}://{}:{}>'.format(self.protocol, self.host, self.port)


class RemoteNetwork(Base):
    __tablename__ = "remote_network"
    id = Column(Integer, primary_key=True)
    token = Column(String(100))
    protocol = Column(String(64), index=True)
    host = Column(String(64), index=True, unique=True)
    port = Column(Integer(), index=True)
    ssl_check = Column(Boolean(), index=True)
    fernet_key = Column(String(100))

    def __repr__(self):
        return '<RemoteNetwork {}://{}:{}>'.format(self.protocol, self.host, self.port)