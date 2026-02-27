"""Token-bucket rate limiter per provider."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Simple token-bucket rate limiter."""
    rpm: int
    _last_request: float = field(default=0.0, init=False)

    @property
    def _min_interval(self) -> float:
        """Minimum seconds between requests."""
        if self.rpm <= 0:
            return 0.0
        return 60.0 / self.rpm

    def wait(self) -> None:
        """Block until we can make the next request."""
        now = time.time()
        elapsed = now - self._last_request
        wait_time = self._min_interval - elapsed
        if wait_time > 0:
            time.sleep(wait_time)
        self._last_request = time.time()
