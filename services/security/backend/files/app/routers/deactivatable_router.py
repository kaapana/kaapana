from abc import ABCMeta, abstractmethod
from functools import wraps
import inspect
from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND


class DeactivatableRouter(metaclass=ABCMeta):
    _activated = False

    @abstractmethod
    def set_activated(self, activated: bool):
        pass

    def activation_wrapper(fn):
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def wrapper(self: DeactivatableRouter, *args, **kwargs):
                if not self._activated:
                    raise HTTPException(
                        status_code=HTTP_404_NOT_FOUND, detail="Route is not active"
                    )

                return await fn(self, *args, **kwargs)

            return wrapper
        else:

            @wraps(fn)
            def wrapper(self: DeactivatableRouter, *args, **kwargs):
                if not self._activated:
                    raise HTTPException(
                        status_code=HTTP_404_NOT_FOUND, detail="Route is not active"
                    )

                return fn(self, *args, **kwargs)

            return wrapper
