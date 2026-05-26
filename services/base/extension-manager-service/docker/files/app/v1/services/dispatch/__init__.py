from .consumers.workflows import WorkflowInstaller
from .content import Content
from .dispatcher import Dispatcher

dispatcher = Dispatcher(installers=[WorkflowInstaller()])
