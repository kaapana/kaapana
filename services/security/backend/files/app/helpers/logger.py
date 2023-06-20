import inspect
import logging
from typing import Union
from helpers.resources import LOGGER_NAME
from functools import wraps

def get_logger(name=LOGGER_NAME, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.hasHandlers():
        logger.propagate = 0
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    
    return logger

def function_logger_factory(logger):
    def function_logger(fn):
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def wrapper(*args, **kwds):
                logger.debug(f"!! Entering {fn.__name__}")
                try:
                    return_val = await fn(*args, **kwds)
                    return return_val
                except Exception as e:
                    logger.debug(f"!! Exception in function: {e}")
                    raise e
                finally:
                    logger.debug(f"!! Exiting {fn.__name__}")

            return wrapper
        else:
            @wraps(fn)
            def wrapper(*args, **kwds):
                logger.debug(f"!! Entering {fn.__name__}")
                try:
                    return_val = fn(*args, **kwds)
                    return return_val
                except Exception as e:
                    logger.debug(f"!! Exception in function: {e}")
                    raise e
                finally:
                    logger.debug(f"!! Exiting {fn.__name__}")

            return wrapper

    return function_logger

def trimContent(content: Union[str, bytes], length: int = 150) -> str:
    if isinstance(content, bytes):
        content = str(content)
    
    if len(content) < length:
        return content
    
    return content[:length] + ".."
