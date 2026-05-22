from uuid import UUID
from .models import ExtensionStatus


class RepositoryExistsException(Exception):
    def __init__(self, repository_id: UUID, name: str):
        self.repository_id = repository_id
        super().__init__(f"Repository with id {repository_id} not found.")


class NotSupportedExtensionStateTransition(Exception):
    def __init__(self, is_state: ExtensionStatus, soll_state: ExtensionStatus):
        super().__init__(
            f"State transition from {is_state} to {soll_state} no supported!"
        )


class LockedExtensionException(Exception):
    def __init__(self, extension_id: UUID):
        super().__init__(f"Database row for extension {extension_id} is locked!")


class LockedRepositoryException(Exception):
    def __init__(self, repository_id: UUID):
        super().__init__(f"Database row for repository {repository_id} is locked!")
