from datetime import datetime

from pydantic import BaseModel


class Measurement(BaseModel):
    metric: str
    value: float
    timestamp: datetime
