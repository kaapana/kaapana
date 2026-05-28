class ConnectionError(Exception):
    """Raised when there is a connection error while trying to connect to the OCI registry."""

    pass


class ExtensionNotFoundException(Exception):
    """Raised when an extension is not found in the OCI registry."""

    pass


class RepositoryNotFoundException(Exception):
    """Raised when a repository is not found in the OCI registry."""

    pass


class ExtensionPullError(Exception):
    """Raised when there is an error while pulling an extension from the OCI registry."""

    pass
