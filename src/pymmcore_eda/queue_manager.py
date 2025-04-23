from __future__ import annotations

from queue import Queue
from threading import Timer
from typing import TYPE_CHECKING

from useq import MDAEvent

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._event_queue import DynamicEventQueue
from pymmcore_eda.time_machine import TimeMachine

if TYPE_CHECKING:
    from pymmcore_eda._eda_sequence import EDASequence
    from pymmcore_eda.actuator import MDAActuator  # should be generalized


class QueueManager:
    """Component responsible to manage events and their timing in front of the Queue.

    Closer description in structure.md.
    """

    def __init__(
        self,
        time_machine: TimeMachine | None = None,
        eda_sequence: EDASequence | None = None,
    ):
        self.acq_queue: Queue = Queue()
        self.stop = object()
        self.acq_queue_iterator = iter(self.acq_queue.get, self.stop)
        self.time_machine = time_machine or TimeMachine()
        self.preemptive = 0.02
        self.t_idx = 0
        self.warmup = 3
        self.next_time = None
        self.event_queue = DynamicEventQueue()

        self.eda_sequence = eda_sequence
        self._axis_max: dict[str, int] = {}
        self.timer = Timer(0, self.queue_next_event)

    def register_actuator(
        self, actuator: MDAActuator, n_channels: int = 1
    ) -> list[int]:
        """Actuator asks for indices for example which channel to push to."""
        self._axis_max["c"] = self._axis_max.get("c", 0) + n_channels
        return list(range(self._axis_max["c"] - n_channels, self._axis_max["c"]))

    def prepare_event(self, event: MDAEvent | EDAEvent) -> EDAEvent:
        """Prepare an event for the queue."""
        if isinstance(event, MDAEvent):
            event = EDAEvent().from_mda_event(event, self.eda_sequence)
        if self.eda_sequence:
            event.sequence = self.eda_sequence
        # Offset time absolute
        if event.min_start_time and event.min_start_time < 0.0:
            start = self.time_machine.event_seconds_elapsed() + abs(
                event.min_start_time
            )
            event.min_start_time = start

        # Add warmup time
        if event.min_start_time:
            event.min_start_time += self.warmup
        else:
            event.min_start_time = self.warmup
        return event

    def register_event(self, event: MDAEvent | EDAEvent) -> None:
        """Actuators call this to request an event to be put on the event_register."""
        event = self.prepare_event(event)
        self.event_queue.add(event)
        self._reset_timer()

    def queue_next_event(self) -> None:
        """Queue the next event."""
        eda_event = self.event_queue.get_next()
        if not eda_event:
            self.stop_seq()
            return
        event = MDAEvent(**eda_event.model_dump())
        self.acq_queue.put(event)
        self._reset_timer()

    def stop_seq(self) -> None:
        """Stop the sequence after the events currently on the queue."""
        self.acq_queue.put(self.stop)

    def empty_queue(self) -> None:
        """Empty the queue."""
        i = 0
        while not self.acq_queue.empty():
            self.acq_queue.get(False)
            i += 1

    def _reset_timer(self) -> None:
        """Set or reset the timer for an event."""
        # If we are the time 0 event and we reset, wait for potential other events to
        # be queued
        self.timer.cancel()
        if len(self.event_queue) == 0:
            return
        self.time_machine.consume_event(self.event_queue.peak_next())
        start_time = self.event_queue.peak_next().min_start_time
        relative_time = (
            start_time - self.time_machine.event_seconds_elapsed() - self.preemptive
        )
        self.timer = Timer(max(relative_time, 0.0), self.queue_next_event)
        self.timer.start()
