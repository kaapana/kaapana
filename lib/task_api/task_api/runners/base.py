from abc import ABC, abstractmethod
from task_api.processing_container import task_models
import logging
from pathlib import Path
import os
import pickle


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
    def dump(cls, task_run: task_models.TaskRun, output: Path = None) -> None:
        """
        Dump task run object as pickle to output.
        """
        output_path = output or Path(os.curdir, f"task_run-{task_run.id}.pkl")
        with open(
            output_path,
            "wb",
        ) as f:
            pickle.dump(
                task_run,
                f,
            )

    @classmethod
    @abstractmethod
    def run(cls, task: task_models.Task) -> task_models.TaskRun:
        """
        Start a processing-container for task
        """
        pass

    @classmethod
    @abstractmethod
    def logs(
        cls,
        task_run: task_models.TaskRun,
        follow: bool,
        startup_timeout: int,
        log_timeout: int,
    ) -> None:
        """
        Print logs to stdout.
        """
        pass

    @classmethod
    @abstractmethod
    def stop(cls, task_run: task_models.TaskRun) -> None:
        """
        Stop the container associated with task_run.
        """
        pass
