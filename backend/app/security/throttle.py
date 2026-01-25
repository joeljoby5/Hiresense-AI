from collections import OrderedDict
from threading import Lock
from time import monotonic

from app.services.errors import AuthenticationBusy


class LoginAttempts:
    def __init__(self):
        self.entries: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self.lock = Lock()

    def check(self, peer: str) -> None:
        timestamp = monotonic()
        with self.lock:
            while self.entries and next(iter(self.entries.values()))[0] <= timestamp:
                self.entries.popitem(last=False)
            expiry, count = self.entries.get(peer, (timestamp + 60, 0))
            if count >= 8 or (peer not in self.entries and len(self.entries) >= 2_048):
                raise AuthenticationBusy()
            self.entries[peer] = (expiry, count + 1)
