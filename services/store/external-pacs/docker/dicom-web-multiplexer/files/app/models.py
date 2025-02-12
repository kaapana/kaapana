from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class DataSourceDB(Base):
    __tablename__ = "DataSources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dcmweb_endpoint = Column(String(255), nullable=False)


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dcmweb_endpoint: str


class DataSourceRequest(BaseModel):
    dcmweb_endpoint: str


class SecretData(BaseModel):
    type: str
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_x509_cert_url: str
    universe_domain: str


class AuthenticatedDataSourceRequest(BaseModel):
    datasource: DataSourceRequest
    secret_data: SecretData


class AuthenticatedDataSourceResponse(BaseModel):
    datasource: DataSourceResponse
    secret_data: SecretData
