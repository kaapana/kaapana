# app/api/v1/services/errors.py
class ServiceError(Exception):
    """Base class for all service-level errors."""


class NotFoundError(ServiceError):
    """Raised when an entity is not found."""


class BadRequestError(ServiceError):
    """Raised for client / bad input errors."""


class DependencyError(ServiceError):
    """Raised when an external dependency (DB, engine, adapter) fails."""


class InternalError(ServiceError):
    """Raised for unexpected internal logic errors."""
