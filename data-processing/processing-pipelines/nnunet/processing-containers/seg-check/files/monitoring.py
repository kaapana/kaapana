import psutil
import threading
import time
from functools import wraps
import os
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


def monitor_system_memory(interval=1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            process = psutil.Process(os.getpid())
            peak_memory = [0]
            stop_event = threading.Event()

            def reporter():
                while not stop_event.is_set():
                    mem = process.memory_info().rss  # in bytes
                    mem_mb = mem / (1024**2)
                    peak_memory[0] = max(peak_memory[0], mem_mb)
                    logger.error(
                        f"[Memory] Current: {mem_mb:.2f} MB | Peak: {peak_memory[0]:.2f} MB"
                    )
                    time.sleep(interval)

            thread = threading.Thread(target=reporter)
            thread.start()

            try:
                return func(*args, **kwargs)
            finally:
                stop_event.set()
                thread.join()
                logger.error(f"[Memory] Final Peak Usage: {peak_memory[0]:.2f} MB")

        return wrapper

    return decorator
