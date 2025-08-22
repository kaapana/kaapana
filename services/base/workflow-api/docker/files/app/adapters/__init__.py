from app.adapters.adapters import *
from app.adapters.base import WorkflowEngineAdapter
from app.adapters.adapters.dummy_adapter import DummyAdapter

from typing import List

from app import schemas
from app.adapters import adapters
import inspect, pkgutil, importlib
from sqlalchemy.ext.asyncio import AsyncSession


def discover_workflow_engine_adapters() -> List[WorkflowEngineAdapter]:
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


def get_workflow_engine(workflow: schemas.Workflow) -> WorkflowEngineAdapter:
    """
    Return the workflow engine defined in the Workflow
    """
    workflow_engine_identifier = workflow.labels.get("kaapana.builtin.workflow_engine")
    for engine in discover_workflow_engine_adapters():
        if workflow_engine_identifier == engine.workflow_engine:
            print(type(engine))
            return engine()

    return DummyAdapter()
