class ConsumerError(Exception):
    """Raised when installation of content fails."""


class ExtensionInstallationError(Exception):
    """Raised when installation of an extension fails."""


class InstallerNotFoundError(Exception):
    """Raised when no installer is found for a given content type."""


class ContentError(Exception):
    """Raised when there is an error with the content of an extension."""
