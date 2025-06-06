from __future__ import annotations

import uuid
from queue import Queue
from threading import Timer
from typing import TYPE_CHECKING, Any

from useq import MDAEvent

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._event_queue import DynamicEventQueue

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus

    from pymmcore_eda._eda_sequence import EDASequence
    from pymmcore_eda.actuator import MDAActuator  # should be generalized
from pymmcore_eda.time_machine import TimeMachine


class QueueManager:
    """Component responsible to manage events and their timing in front of the Queue.

    Closer description in structure.md.
    """

    def __init__(
        self,
        mmcore: CMMCorePlus | None = None,
        eda_sequence: EDASequence | None = None,
        time_machine: TimeMachine | None = None,
    ):
        self.acq_queue: Queue = Queue()
        self.stop = object()
        self.acq_queue_iterator = iter(self.acq_queue.get, self.stop)

        self.mmc = mmcore
        self.time_machine: TimeMachine = time_machine
        if self.mmc:
            self.time_machine = time_machine or self.mmc.mda
            self.mmc.mda.events.sequencePauseToggled.connect(self.toggle_pause)
            self.mmc.mda.events.sequenceCanceled.connect(self.stop_seq)
        if not self.time_machine:
            self.time_machine = TimeMachine()

        self.preemptive = 0.0
        self.t_idx = 0
        self.warmup = 3
        self.reset_correction = 0
        self.paused_time = 0.0
        self.next_time = None
        self.event_queue = DynamicEventQueue()
        self.can_reset = True
        self.canceled = False

        self.actuators: dict[str, dict[str, Any]] = {}

        self.eda_sequence = eda_sequence
        self._axis_max: dict[str, int] = {}
        self.timer = Timer(0, self._queue_next_event)

    def register_actuator(
        self, actuator: MDAActuator, n_channels: int = 1
    ) -> dict[str, Any]:
        """Actuator wants to register events in the future."""
        settings: dict[str, Any] = {}
        self._axis_max["c"] = self._axis_max.get("c", 0) + n_channels
        settings["channels"] = list(
            range(self._axis_max["c"] - n_channels, self._axis_max["c"])
        )
        # Only one actuator can reset the timer at the beginning
        settings["can_reset"] = self.can_reset
        settings["id"] = str(uuid.uuid4())
        self.can_reset = False
        self.actuators[settings["id"]] = settings
        return settings

    def prepare_event(
        self, event: MDAEvent | EDAEvent, actuator_id: str = "0"
    ) -> EDAEvent:
        """Prepare an event for the queue."""
        if isinstance(event, MDAEvent):
            event = EDAEvent().from_mda_event(event, self.eda_sequence)
        if self.eda_sequence and event.sequence is None:
            event.sequence = self.eda_sequence

        if event.reset_event_timer and actuator_id in self.actuators.keys():
            event.reset_event_timer = self.actuators[actuator_id]["can_reset"]

        # Offset time absolute
        if event.min_start_time and event.min_start_time < 0.0:
            start = self.time_machine.event_seconds_elapsed() + abs(
                event.min_start_time
            )
            event.min_start_time = start

        if event.reset_event_timer and self.t_idx > 0:
            self.warmup = 0
            self.reset_correction = event.min_start_time

        return event

    def register_event(
        self, event: MDAEvent | EDAEvent, actuator_id: str = "0"
    ) -> None:
        """Actuators call this to request an event to be put on the event_register."""
        event = self.prepare_event(event, actuator_id)
        self.event_queue.add(event)
        if event == self.event_queue.peak_next():
            self._reset_timer()

    def _queue_next_event(self) -> None:
        """Queue the next event."""
        eda_event = self.event_queue.get_next()
        if not eda_event:
            self.stop_seq()
            return
        event = eda_event.to_mda_event()
        self.acq_queue.put(event)
        wait = 0.05 if event.reset_event_timer else 0.0
        if not self.canceled:
            Timer(wait, self._reset_timer).start()
            self.t_idx = event.index.get("t", 0)

    def stop_seq(self) -> None:
        """Stop the sequence after the events currently on the queue."""
        self.canceled = True
        self.timer.cancel()
        self.acq_queue.put(self.stop)

    def empty_queue(self) -> None:
        """Empty the queue."""
        i = 0
        while not self.acq_queue.empty():
            self.acq_queue.get(False)
            i += 1

    def _reset_timer(self) -> None:
        """Set or reset the timer for an event."""
        self.timer.cancel()
        if len(self.event_queue) == 0:
            return
        if self.time_machine and hasattr(self.time_machine, "consume_event"):
            self.time_machine.consume_event(self.event_queue.peak_next())

        next_event = self.event_queue.peak_next()
        if not next_event.min_start_time:
            next_event.min_start_time = 0.0
        if next_event.reset_event_timer:
            relative_time = next_event.min_start_time + self.warmup
        else:
            relative_time = (
                next_event.min_start_time
                - self.time_machine.event_seconds_elapsed()
                - self.reset_correction
                + self.paused_time
            )

        self.timer = Timer(max(relative_time, 0.0), self._queue_next_event)
        self.timer.start()

    def toggle_pause(self, paused: bool) -> None:
        """Toggle the pause state of the sequence."""
        if paused:
            self.timer.cancel()
            self.paused_start = self.time_machine.event_seconds_elapsed()
        else:
            self.paused_time += (
                self.time_machine.event_seconds_elapsed() - self.paused_start
            )
            self._reset_timer()
