from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class Measurement(BaseModel):
    metric: str
    value: float
    timestamp: datetime
