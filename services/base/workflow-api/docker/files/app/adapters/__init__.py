from app.adapters.adapters import *
from app.adapters.base import WorkflowEngineAdapter

from typing import List

from app import schemas
from app.adapters import adapters
import inspect, pkgutil, importlib


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


def get_workflow_engine(workflow_run_create: schemas.WorkflowRunCreate):
    """
    Return the workflow engine specified in the Workflow Run
    """

    workflow_engine_identifier = workflow_run_create.labels.get(
        "kaapana.builtin.workflow_engine"
    )
    for engine in discover_workflow_engine_adapters():
        if workflow_engine_identifier == engine.workflow_engine:
            return engine

    return WorkflowEngineAdapter
