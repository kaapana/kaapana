from .consumers.workflows import WorkflowInstaller
from .dispatcher import Dispatcher
from .content import Content

dispatcher = Dispatcher(installers=[WorkflowInstaller()])
