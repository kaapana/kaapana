from pydantic import BaseModel
from datetime import datetime, timezone
import logging
from helpers.logger import function_logger_factory, get_logger
from helpers.resources import LOGGER_NAME

logger = get_logger(f"{LOGGER_NAME}.jwt_token_model", logging.INFO)


class JWTToken(BaseModel):
    token: str
    expiration_date: datetime

    def is_expired(self) -> bool:
        return self.token == "" or self.expiration_date <= datetime.now(timezone.utc)

    def get_seconds_until_expiration(self) -> int:
        return (self.expiration_date - datetime.now(timezone.utc)).total_seconds()

    @function_logger_factory(logger)
    def expired_or_expires_soon(self, expires_soon_seconds=30) -> bool:
        if self.token == "":
            logger.debug("no token saved")
            return True

        if self.is_expired():
            logger.debug("token is expired")
            return True

        if self.get_seconds_until_expiration() < expires_soon_seconds:
            logger.debug(
                f"expiration date of token is in less than {expires_soon_seconds}s"
            )
            return True

        logger.debug("token does not expire in the next 30s")
        return False
