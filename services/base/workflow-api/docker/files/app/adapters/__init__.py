import importlib
import inspect
import logging
import pkgutil
from typing import List, Type

from app.adapters import adapters
from app.adapters.adapters import *
from app.adapters.adapters.dummy_adapter import DummyAdapter
from app.adapters.base import WorkflowEngineAdapter

logger = logging.getLogger(__name__)


def discover_workflow_engine_adapters() -> List[Type[WorkflowEngineAdapter]]:
    """
    Discover all workflow engine adapters in the code base
    """
    discovered_adapters = []
    for _, modname, _ in pkgutil.walk_packages(
        adapters.__path__, adapters.__name__ + "."
    ):
        module = importlib.import_module(modname)
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(cls, WorkflowEngineAdapter)
                and cls is not WorkflowEngineAdapter
            ):
                discovered_adapters.append(cls)
    logger.info(f"Discovered adapters: {discovered_adapters=}")
    return discovered_adapters


def get_workflow_engine(workflow_engine: str) -> WorkflowEngineAdapter:
    """
    Return the workflow engine defined in the Workflow
    """
    for engine in discover_workflow_engine_adapters():
        if workflow_engine.lower() == engine.workflow_engine.lower():
            return engine()

    return DummyAdapter()
