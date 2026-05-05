from .consumers.workflows import WorkflowContent, WorkflowInstaller, WorkflowDiscovery
from .extension import Extension, ExtensionInstaller, ExtensionDiscovery

Installer = ExtensionInstaller(installers=[WorkflowInstaller()])
Discovery = ExtensionDiscovery(content_discoveries=[WorkflowDiscovery()])
