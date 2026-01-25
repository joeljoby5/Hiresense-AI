from uuid import UUID

from fastapi import Request

from app.api.session_security import is_loopback, require_csrf, require_origin, session_token
from app.services.errors import IdentityUnavailableError


def resolve_owner(request: Request) -> UUID:
    config = request.app.state.settings
    token = session_token(request)
    unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
    if token is not None:
        if unsafe:
            require_csrf(request, token)
        return request.app.state.accounts.current(token).profile.id
    if (config.environment != "development" or not config.development_identity_enabled
            or config.development_owner_id is None or not is_loopback(request)):
        raise IdentityUnavailableError()
    if unsafe and "origin" in request.headers:
        require_origin(request)
    return config.development_owner_id
