import itertools
from collections.abc import Iterable, Iterator
from threading import Event, Timer
from typing import cast

from pymmcore_plus._logger import exceptions_logged, logger
from pymmcore_plus.mda._protocol import PMDAEngine
from pymmcore_plus.mda._runner import MDARunner
from useq import MDAEvent


class DynamicRunner(MDARunner):
    """DynamicRunner is a subclass of MDARunner that handles dynamic acquisitions."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.acquisition_timer: Timer = Timer(0, self.acquire_event)
        self._events: Iterator[MDAEvent] = iter([])
        self._acquisition_complete = Event()
        self._next_event: MDAEvent | None = None

    def _run(self, engine: PMDAEngine, events: Iterable[MDAEvent]) -> None:
        """Main execution of events, inside the try/except block of `run`."""
        event_iterator = getattr(engine, "event_iterator", iter)
        self._events = event_iterator(events)
        self._reset_event_timer()
        self._sequence_t0 = self._t0
        self.set_timer()
        self._acquisition_complete.wait()

    def set_timer(self) -> None:
        """Set the timer for the next event."""
        if not self._peek_next_event():
            self._acquisition_complete.set()
            return

        event = self._next_event
        assert event is not None
        if event.reset_event_timer:
            self._reset_event_timer()

        if event.min_start_time:
            go_at = event.min_start_time + self._paused_time
            remaining_wait_time = go_at - self.event_seconds_elapsed()
        else:
            remaining_wait_time = 0.0

        # Set the timer to call acquire_event after the next time
        self.acquisition_timer = Timer(remaining_wait_time, self.acquire_event)
        self.acquisition_timer.start()

    def acquire_event(self) -> None:
        assert self.engine is not None
        teardown_event = getattr(self.engine, "teardown_event", lambda e: None)
        event = next(self._events)
        self._signals.eventStarted.emit(event)
        logger.info("%s", event)
        self.engine.setup_event(event)

        try:
            runner_time_ms = self.seconds_elapsed() * 1000
            # this is a bit of a hack to pass the time into the engine
            # it is used for intra-event time calculations inside the engine.
            # we pop it off after the event is executed.
            event.metadata["runner_t0"] = self._sequence_t0
            output = self.engine.exec_event(event) or ()  # in case output is None
            for payload in output:
                img, event, meta = payload
                event.metadata.pop("runner_t0", None)
                # if the engine calculated its own time, don't overwrite it
                if "runner_time_ms" not in meta:
                    meta["runner_time_ms"] = runner_time_ms
                with exceptions_logged():
                    self._signals.frameReady.emit(img, event, meta)
        finally:
            teardown_event(event)
            self.set_timer()

    def _peek_next_event(self) -> bool:
        try:
            next_event = next(self._events)
            self._next_event = next_event
            # Put the event back by chaining it with the rest of the iterator
            self._events = cast(
                Iterator[MDAEvent], itertools.chain([next_event], self._events)
            )
            return True
        except StopIteration:
            self._next_event = None
            return False
