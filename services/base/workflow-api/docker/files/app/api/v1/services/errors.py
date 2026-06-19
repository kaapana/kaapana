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


class ConflictError(ServiceError):
    """Raised when a request conflicts with current state (e.g. already in progress)."""


class ValidationError(ServiceError):
    """Raised when input is structurally valid but semantically rejected."""
