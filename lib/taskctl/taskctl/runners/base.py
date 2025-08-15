from abc import ABC, abstractmethod
from taskctl.processing_container import models
import logging
from pathlib import Path
import os
import json


class BaseRunner(ABC):
    """
    Base class for all task runners.
    Task runners have to inerhit from this class and overwrite all abstract methods
    """

    _logger = logging.getLogger(__name__)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # This runs whenever a subclass is created.
        cls._logger = logging.getLogger(f"{cls.__module__}.{cls.__name__}")

    @classmethod
    def set_logger(cls, logger: logging.Logger):
        """
        Set a custom logger for the runner.
        """
        cls._logger = logger

    @classmethod
    def dump(cls, task_run: models.TaskRun, output: Path = None):
        """
        Write json model of task_run to output.
        """
        output_path = output or Path(os.curdir, f"task_run-{task_run.id}.json")
        with open(
            output_path,
            "w",
        ) as f:
            json.dump(
                task_run.model_dump(
                    mode="json",
                    exclude={"full_object"},
                    exclude_none=True,
                    exclude_unset=True,
                    exclude_defaults=True,
                ),
                f,
                indent=2,
            )

    @classmethod
    @abstractmethod
    def run(cls, task: models.Task, dry_run: bool = False) -> models.TaskRun:
        pass

    @classmethod
    @abstractmethod
    def logs(cls, task_run: models.TaskRun, follow: bool = True):
        pass

    @classmethod
    @abstractmethod
    def stop(cls, task_run: models.TaskRun):
        pass
