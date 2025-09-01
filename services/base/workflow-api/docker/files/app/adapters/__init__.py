import logging
from app.adapters.adapters import *
from app.adapters.base import WorkflowEngineAdapter
from app.adapters.adapters.dummy_adapter import DummyAdapter

from typing import List, Type

from app import schemas
from app.adapters import adapters
import inspect, pkgutil, importlib

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
    return discovered_adapters


def get_workflow_engine(workflow_labels: List[schemas.Label]) -> WorkflowEngineAdapter:
    """
    Return the workflow engine defined in the Workflow
    """
    workflow_engine_id = ""
    for label in workflow_labels:
        if label.key == "kaapana.builtin.workflow_engine":
            workflow_engine_id = label.value
            break
    for engine in discover_workflow_engine_adapters():
        if workflow_engine_id == engine.workflow_engine:
            logger.info(f"Using workflow engine: {engine.workflow_engine}")
            return engine()

    return DummyAdapter()
