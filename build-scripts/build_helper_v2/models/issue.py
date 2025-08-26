import logging
from typing import List, Optional

from pydantic import BaseModel


class Issue(BaseModel):
    component: str
    name: str
    msg: str
    level: str
    output: List[str]
    path: Optional[str] = None

    def log_self(self, logger: logging.Logger):
        """Logs this issue using the provided logger."""
        logger.warning("")
        logger.warning(f"{self.level} -> {self.component}:{self.name}")
        logger.warning(f"msg={self.msg}")
        logger.warning("\n".join(self.output))
        logger.warning("")
        logger.warning("-----------------------------------------------------------")
