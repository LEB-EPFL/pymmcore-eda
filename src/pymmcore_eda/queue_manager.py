from __future__ import annotations

from typing import TYPE_CHECKING

from useq import MDAEvent

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._event_queue import DynamicEventQueue

if TYPE_CHECKING:
    from pymmcore_eda._eda_sequence import EDASequence
    from pymmcore_eda.actuator import MDAActuator  # should be generalized
    from pymmcore_eda.time_machine import TimeMachine


class QueueManager:
    """Component responsible to manage events and their timing in front of the Queue.

    Closer description in structure.md.
    """

    def __init__(
        self,
        time_machine: TimeMachine | None = None,
        eda_sequence: EDASequence | None = None,
    ):
        # self.acq_queue: Queue = Queue()
        self.stop = object()
        self.event_queue = DynamicEventQueue(self.stop)
        self.acq_queue_iterator = iter(self.event_queue.get, self.stop)
        self.t_idx = 0
        self.warmup = 3
        self.next_time = None

        # self.time_machine = time_machine or TimeMachine()
        self.eda_sequence = eda_sequence
        self._axis_max: dict[str, int] = {}

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
        # if event.min_start_time and event.min_start_time < 0.0:
        #     start = self.time_machine.event_seconds_elapsed() + abs(
        #         event.min_start_time
        #     )
        #     event.min_start_time = start

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

    def stop_seq(self) -> None:
        """Stop the sequence after the events currently on the queue."""
        self.event_queue.stopped = True

    def empty_queue(self) -> None:
        """Empty the queue."""
        i = 0
        while not self.event_queue.empty():
            self.event_queue.get(False)
            i += 1
