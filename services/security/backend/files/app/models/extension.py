from pydantic import BaseModel, Field #, validator
from enum import Enum
from typing import List, Optional

class ExtensionType(Enum):
    WAZUH = 1
    STACKROX = 2
    UNKNOWN = 999

class ExtensionAPIEndpoints(BaseModel):
    identifier: Optional[str] = Field(None, description="An identifier to distinguish endpoints if there are multiple.")
    endpoint: str = Field(..., description="The URI that the API is reachable at.")

class ExtensionRegistration(BaseModel):
    name: str = Field(..., description="The name of the extension.")
    api_endpoints: List[ExtensionAPIEndpoints] = Field(..., description="All API endpoints of the extension.", min_items=1)
    
    # @validator('type')
    # def type_validator(cls, type):
    #     return type or ExtensionType.UNKNOWN
        