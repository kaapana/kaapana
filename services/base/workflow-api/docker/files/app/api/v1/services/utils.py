from app.dependencies import get_async_db
from typing import Any, Callable, Coroutine
import logging
import asyncio

logger = logging.getLogger(__name__)


async def run_in_background_with_retries(
    func: Callable[..., Coroutine[Any, Any, Any]],
    *args,
    max_retries: int = 3,
    delay_seconds: float = 5.0,
    **kwargs,
) -> None:
    """
    Run an async function in the background with automatic retries.

    Args:
        func: The async function to execute.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.
        max_retries: Maximum number of retries before giving up.
        delay_seconds: exponential backoff, i.e. `delay_seconds * (2 ** (attempt - 1))` is used between retries .

    Returns:
        None. Runs asynchronously and logs outcomes.
    """
    for attempt in range(1, max_retries + 1):
        try:
            # create a new session if func requires 'db'
            if "db" in kwargs:
                async for new_db in get_async_db():
                    kwargs["db"] = new_db
                    await func(*args, **kwargs)
            else:
                await func(*args, **kwargs)
            logger.debug(f"Background task {func.__name__} completed successfully.")
            return
        except Exception as e:
            logger.warning(
                f"Attempt {attempt}/{max_retries} failed for {func.__name__}: {e}"
            )
            if attempt == max_retries:
                logger.error(
                    f"All {max_retries} retries failed for background task {func.__name__}"
                )
                return
            await asyncio.sleep(
                delay_seconds * (2 ** (attempt - 1))
            )  # exponential backoff
