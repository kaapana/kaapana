import logging

# from helpers.resources import LOGGER_NAME
from functools import wraps
from pathlib import Path


def get_logger(name, level=logging.DEBUG, log_file=None):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        logger.propagate = False
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter("%(levelname)s - %(asctime)s - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    if log_file:
        fh = logging.FileHandler(log_file, mode="w")
        fh.setLevel(logging.DEBUG)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter("%(levelname)s - %(asctime)s - %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def function_logger_factory(logger):
    def function_logger(fn):
        @wraps(fn)
        def wrapper(*args, **kwds):
            logger.debug(f"!! Entering {fn.__name__}")
            return_val = fn(*args, **kwds)
            logger.debug(f"!! Exiting {fn.__name__}")
            return return_val

        return wrapper

    return function_logger


def add_log_file(name: str, log_file: str, level: int = logging.DEBUG):
    """Add a file handler to an existing logger by name.

    - Creates parent directories for `log_file` if possible.
    - Avoids adding duplicate FileHandler for the same filename.
    - Returns the logger instance.
    """
    logger = logging.getLogger(name)
    # Ensure logger has a level set
    if logger.level == 0:
        logger.setLevel(level)

    resolved = Path(log_file)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    for h in list(logger.handlers):
        if isinstance(h, logging.FileHandler):
            try:
                if Path(getattr(h, "baseFilename", "")).resolve() == resolved.resolve():
                    return logger
            except Exception:
                # ignore resolution errors and continue
                pass

    fh = logging.FileHandler(str(resolved), mode="a", encoding="utf-8")
    fh.setLevel(level)
    formatter = logging.Formatter("%(levelname)s - %(asctime)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger
