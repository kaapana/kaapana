import logging
from functools import wraps


def get_logger(name, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        logger.propagate = 0
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

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
