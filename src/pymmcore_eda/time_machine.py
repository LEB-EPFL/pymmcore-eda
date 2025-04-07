from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from useq import MDAEvent


class TimeMachine:
    """Component to sync time between the Runner in pymmcore-plus and QueueManager.

    This avoids having direct connections between the two components.
    Like this seems to be accurate enough (10ms).
    """

    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def consume_event(self, event: MDAEvent) -> None:
        """Check for reset_event_timer and update the internal timer."""
        if event.reset_event_timer:
            self._t0 = time.perf_counter()

    def event_seconds_elapsed(self, *_: Any) -> float:
        """Synced timer with the Runner in pymmcore-plus."""
        return time.perf_counter() - self._t0

    def reset_timer(self) -> None:
        """Reset the timer."""
        self._t0 = time.perf_counter()
