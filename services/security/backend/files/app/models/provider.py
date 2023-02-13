from pydantic import BaseModel, Field #, validator
from enum import Enum
from typing import List, Optional

class ProviderType(Enum):
    WAZUH = 1
    STACKROX = 2
    UNKNOWN = 999

class ProviderAPIEndpoints(BaseModel):
    identifier: Optional[str] = Field(None, description="An identifier to distinguish endpoints if there are multiple.")
    endpoint: str = Field(..., description="The URI that the API is reachable at.")

class ProviderRegistration(BaseModel):
    name: str = Field(..., description="The name of the provider.")
    url: str = Field(..., description="The main url of the provider (usually access to UI).") 
    api_endpoints: List[ProviderAPIEndpoints] = Field(..., description="All API endpoints of the extension.", min_items=1)

class InternalProviderRegistration(ProviderRegistration):
    id: str = Field(..., description="The ID of the provider.")

    def get_overview(self) -> dict:
        return dict(id = self.id, name = self.name, url = self.url, api_endpoints = self.api_endpoints)
    
    # @validator('type')
    # def type_validator(cls, type):
    #     return type or ExtensionType.UNKNOWN
        