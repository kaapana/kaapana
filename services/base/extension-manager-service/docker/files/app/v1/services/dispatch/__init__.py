from .consumers.workflows import WorkflowInstaller
from .extension import Extension, ExtensionInstaller
from .content import Content

Installer = ExtensionInstaller(installers=[WorkflowInstaller()])
