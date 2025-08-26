import logging
from pathlib import Path


class CustomLogger:
    def __init__(
        self,
        build_dir: Path,
        log_level: str = "DEBUG",
        logger_name: str = "kaapana_build",
    ):
        self.logger = logging.getLogger(logger_name)
        self.logger.propagate = False

        # Clear existing handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        self.formatter = logging.Formatter(fmt="%(levelname)s - %(message)s")

        build_dir.mkdir(parents=True, exist_ok=True)

        # File handler
        self.file_handler = logging.FileHandler(build_dir / "build.log")
        self.file_handler.setFormatter(self.formatter)

        # Console handler
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(self.formatter)

        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

        # Set initial level for logger and handlers
        self.set_level(log_level)

    def set_level(self, level_name: str):
        level = getattr(logging, level_name.upper(), None)
        if level is None:
            raise ValueError(f"Invalid log level: {level_name}")

        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)

    def get_logger(self) -> logging.Logger:
        return self.logger

    def set_console_level(self, level_name: str):
        level = getattr(logging, level_name.upper(), None)
        if level is None:
            raise ValueError(f"Invalid console log level: {level_name}")
        self.console_handler.setLevel(level)

    def set_file_level(self, level_name: str):
        level = getattr(logging, level_name.upper(), None)
        if level is None:
            raise ValueError(f"Invalid file log level: {level_name}")
        self.file_handler.setLevel(level)
