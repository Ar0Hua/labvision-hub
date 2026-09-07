from collections import OrderedDict
from threading import Lock
import hashlib
import time


class TaskRegistry:
    """Bounded process-local replay guard for a signed dispatch attempt."""

    def __init__(self, max_entries: int = 10_000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, int] = OrderedDict()
        self._lock = Lock()

    def accept(self, token: str, expires_at: int, *, now: int | None = None) -> bool:
        current = int(time.time()) if now is None else now
        key = hashlib.sha256(token.encode()).hexdigest()
        with self._lock:
            expired = [entry for entry, expiry in self._entries.items() if expiry < current]
            for entry in expired:
                self._entries.pop(entry, None)
            if key in self._entries:
                return False
            self._entries[key] = expires_at
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
            return True
