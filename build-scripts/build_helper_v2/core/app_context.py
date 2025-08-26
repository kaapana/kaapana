# core/context.py
import logging
from typing import Optional

from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.models.build_state import BuildState
from build_helper_v2.models.platform_config import PlatformConfig


class AppContext:
    def __init__(
        self, config: BuildConfig, logger: logging.Logger, build_state: BuildState
    ):
        self.config = config
        self.logger = logger
        self.build_state = build_state
        self.platform_config: Optional[PlatformConfig] = None

    def get_platform_config(self) -> PlatformConfig:
        if not self.platform_config:
            raise RuntimeError("PlatformConfig not initialized")
        return self.platform_config

    def set_platform_config(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.logger.debug("Platform config set.")
