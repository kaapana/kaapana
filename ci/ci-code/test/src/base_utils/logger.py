import logging

# from helpers.resources import LOGGER_NAME
from functools import wraps


def get_logger(name, level=logging.DEBUG, log_file=None):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        logger.propagate = 0
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
