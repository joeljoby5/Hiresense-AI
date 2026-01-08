class NotFoundError(Exception):
    """No resource exists within the requested owner boundary."""

class RevisionConflictError(Exception):
    """Expected draft revision is stale; future HTTP mapping: 409."""

    def __init__(self, message: str, current_revision: int | None = None):
        super().__init__(message)
        self.current_revision = current_revision
