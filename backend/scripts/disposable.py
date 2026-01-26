"""Cleanup shared by the disposable verification runners."""
from pathlib import Path
from time import monotonic, sleep


def remove_test_database(path: Path) -> None:
    deadline = monotonic() + 4
    while True:
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError as exc:
            if getattr(exc, "winerror", None) != 32 or monotonic() >= deadline:
                raise
            sleep(0.1)
