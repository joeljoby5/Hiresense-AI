class IdentityUnavailableError(Exception):
    """No active internal ownership context is available."""


class AuthenticationRequired(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class CsrfRejected(Exception):
    pass


class AccountExists(Exception):
    pass


class AuthenticationBusy(Exception):
    pass
