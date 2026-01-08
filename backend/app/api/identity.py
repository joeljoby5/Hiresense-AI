from ipaddress import ip_address
from uuid import UUID

from fastapi import Request

from app.services.errors import IdentityUnavailableError


def resolve_owner(request: Request) -> UUID:
    config = request.app.state.settings
    try:
        local_peer = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        local_peer = False
    if (config.environment != "development" or not config.development_identity_enabled
            or config.development_owner_id is None or not local_peer):
        raise IdentityUnavailableError()
    return config.development_owner_id
