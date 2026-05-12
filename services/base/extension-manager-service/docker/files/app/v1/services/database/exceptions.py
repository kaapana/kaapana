class RepositoryNotFoundException(Exception):
    def __init__(self, repository_id: str):
        self.repository_id = repository_id
        super().__init__(f"Repository with id {repository_id} not found.")


class RepositoryExistsException(Exception):
    def __init__(self, repository_id: str, name: str):
        self.repository_id = repository_id
        super().__init__(f"Repository with id {repository_id} not found.")
