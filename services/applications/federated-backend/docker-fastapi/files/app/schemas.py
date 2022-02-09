from typing import Optional

from pydantic import BaseModel


class ClientNetworkBase(BaseModel):
    ssl_check: bool
    allowed_dags: list
    allowed_datasets: list
    automatic_update: bool = False
    automatic_job_execution: bool = False


class ClientNetworkCreate(ClientNetworkBase):
    fernet_encrypted: bool


class ClientNetwork(ClientNetworkBase):
    id: int
    token: str
    protocol: str
    host: str
    port: int
    fernet_key: str

    class Config:
        orm_mode = True


class RemoteNetworkBase(BaseModel):
    token: str
    host: str
    port: int
    fernet_key: str
    ssl_check: bool


class RemoteNetworkCreate(RemoteNetworkBase):
    pass


class RemoteNetwork(RemoteNetworkBase):
    id: int
    # allowed_dags: list
    # allowed_datasets: list
    protocol: str

    class Config:
        orm_mode = True
