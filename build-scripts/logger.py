import logging
from pathlib import Path


class CustomLogger:
    def __init__(
        self,
        build_dir: Path,
        initial_level: str = "DEBUG",
        logger_name: str = "kaapana_build",
    ):
        self.logger = logging.getLogger(logger_name)
        self.logger.propagate = False

        # Clear existing handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        self.formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        build_dir.mkdir(parents=True, exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(build_dir / "build.log")
        file_handler.setFormatter(self.formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Set initial level for logger and handlers
        self.set_level(initial_level)

    def set_level(self, level_name: str):
        level = getattr(logging, level_name.upper(), None)
        if level is None:
            raise ValueError(f"Invalid log level: {level_name}")

        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)

    def get_logger(self) -> logging.Logger:
        return self.logger
