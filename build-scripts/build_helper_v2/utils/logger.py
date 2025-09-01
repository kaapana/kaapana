import logging
from pathlib import Path

LOGGER_NAME = "kaapana_build"


def get_logger():
    return logging.getLogger(LOGGER_NAME)


def init_logger(build_dir: Path, log_level: str = "DEBUG") -> logging.Logger:
    """Initialize the global logger. Call once at program start."""
    build_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(fmt="%(levelname)s - %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(build_dir / "build.log")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    level = getattr(logging, log_level.upper(), logging.DEBUG)
    logger.setLevel(level)
    for h in logger.handlers:
        h.setLevel(level)

    return logger


# Optional convenience functions for dynamic level changes
def set_global_level(level_name: str):
    level = getattr(logging, level_name.upper(), None)
    if level is None:
        raise ValueError(f"Invalid log level: {level_name}")
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    for h in logger.handlers:
        h.setLevel(level)


def set_console_level(level_name: str):
    level = getattr(logging, level_name.upper(), None)
    if level is None:
        raise ValueError(f"Invalid console log level: {level_name}")
    logger = logging.getLogger(LOGGER_NAME)
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler):
            h.setLevel(level)


def set_file_level(level_name: str):
    level = getattr(logging, level_name.upper(), None)
    if level is None:
        raise ValueError(f"Invalid file log level: {level_name}")
    logger = logging.getLogger(LOGGER_NAME)
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler):
            h.setLevel(level)
