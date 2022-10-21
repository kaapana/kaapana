from pydantic import BaseModel
from typing import Optional, List, Dict

class Installation(BaseModel):
    name: str
    version: str
    keywords: Optional[List[str]]
    parameters: Optional[Dict]
    release_name: Optional[str]