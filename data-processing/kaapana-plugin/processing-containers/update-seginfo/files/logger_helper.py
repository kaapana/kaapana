from kaapanapy.logger import get_logger
from functools import wraps

def get_logger(name, level=logging.DEBUG):
    logger = get_logger(__name__)
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
