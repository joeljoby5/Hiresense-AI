class NotFoundError(Exception):
    """No resource exists within the requested owner boundary."""

class RevisionConflictError(Exception):
    """Expected draft revision is stale; future HTTP mapping: 409."""
