import logging
import functools

logger = logging.getLogger("uvicorn")


def deprecated(
    message: str = None, method: str = None, path: str = None, replacement: str = None
):
    """
    Mark an endpoint as deprecated.

    Parameters
    ----------
    message:
        Custom log message. If omitted, a structured default is generated.
    method:
        HTTP method (for logging clarity).
    path:
        Route path (for logging clarity).
    replacement:
        New endpoint to use instead.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            parts = ["API_DEPRECATION -"]

            if method:
                parts.append(f"{method}")
            if path:
                parts.append(f"{path}")
            if replacement:
                parts.append(f"- Replacement: {replacement}")

            if message:
                parts.append(message)
            else:
                parts.append(
                    f"- Endpoint is deprecated and may be removed in future versions."
                )

            logger.warning(" ".join(parts))

            return await func(*args, **kwargs)

        return wrapper

    return decorator
