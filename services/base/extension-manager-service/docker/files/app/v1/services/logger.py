import inspect
import logging
import os
from functools import wraps

LOG_LEVEL = os.getenv("KAAPANA_LOG_LEVEL") or os.getenv("DEBUG_LEVEL") or "INFO"


def get_logger(name, level=None):
    """Return a custom Kaapana logger."""
    logger = logging.getLogger(name)
    level = level or LOG_LEVEL
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
    """Decorator factory that logs entry/exit for both sync and async functions."""
    def function_logger(fn):
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args, **kwds):
                logger.debug(f"!! Entering {fn.__name__}")
                return_val = await fn(*args, **kwds)
                logger.debug(f"!! Exiting {fn.__name__}")
                return return_val
            return async_wrapper
        else:
            @wraps(fn)
            def sync_wrapper(*args, **kwds):
                logger.debug(f"!! Entering {fn.__name__}")
                return_val = fn(*args, **kwds)
                logger.debug(f"!! Exiting {fn.__name__}")
                return return_val
            return sync_wrapper

    return function_logger
