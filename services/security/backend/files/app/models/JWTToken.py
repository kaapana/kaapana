from pydantic import BaseModel
from datetime import datetime, timezone

class JWTToken(BaseModel):
    token: str
    expiration_date: datetime

    def is_expired(self) -> bool:
        return self.token == "" or self.expiration_date <= datetime.now(timezone.utc)
    
    def get_seconds_until_expiration(self) -> int:
        return (self.expiration_date - datetime.now(timezone.utc)).total_seconds()