from __future__ import annotations

from queue import Queue
from threading import Timer
from typing import TYPE_CHECKING
import numpy as np

from pymmcore_eda.time_machine import TimeMachine
from pymmcore_eda._event_queue import DynamicEventQueue
from useq import MDAEvent
from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._eda_sequence import EDASequence


if TYPE_CHECKING:
    from useq import MDAEvent
    from pymmcore_eda._eda_event import EDAEvent


class QueueManager:
    """Component responsible to manage events and their timing in front of the Queue.

    Closer description in structure.md.
    """

    def __init__(self, time_machine: TimeMachine | None = None, eda_sequence: EDASequence | None = None):
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
        # self.axis_order = 'tpgcz' we might need this

    def register_actuator(self, actuator, n_channels: int = 1):
        """Actuator asks for indices for example which channel to push to."""
        self._axis_max['c'] = self._axis_max.get('c', 0) + n_channels
        return list(range(self._axis_max['c']-n_channels, self._axis_max['c']))

    def register_event(self, event: MDAEvent|EDAEvent):
        """Actuators call this to request an event to be put on the event_register."""
        if isinstance(event, MDAEvent):
            event = EDAEvent().from_mda_event(event, self.eda_sequence)
        if self.eda_sequence and event.sequence is None:
            event.sequence = self.eda_sequence

        # Offset time
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

        # Handle frap maps
        if event.metadata:
            if event.metadata.get('0',0)[0] is not None:
                events = self.event_queue.get_events_at_time(event.min_start_time)
                for other_event in events:
                    if other_event.metadata.get('0',0)[0] is not None:
                        event.metadata['0'][0] = np.logical_or(
                            event.metadata['0'][0], other_event.metadata['0'][0]
                        )
                        self.event_queue._events.remove(other_event)

        
        self.event_queue.add(event)
        self._reset_timer()
        # for k, v in event.index.items():
        #     self._axis_max[k] = max(self._axis_max.get(k, 0), v)

    def queue_next_event(self):
        """Queue the next event."""
        eda_event = self.event_queue.get_next()
        if not eda_event:
            self.stop_seq()
            return
        event = MDAEvent(**eda_event.model_dump())
        self.acq_queue.put(event)
        self._reset_timer()


    def stop_seq(self):
        """Stop the sequence after the events currently on the queue."""
        self.acq_queue.put(self.stop)

    def empty_queue(self):
        """Empty the queue."""
        i = 0
        while not self.acq_queue.empty():
            self.acq_queue.get(False)
            i+=1
        print(f"Emptied the queue of {i} events.")

    def _reset_timer(self):
        """Set or reset the timer for an event."""
        #If we are the time 0 event and we reset, wait for potential other events to be queued
        self.timer.cancel()
        if len(self.event_queue._events) == 0:
            return
        self.time_machine.consume_event(self.event_queue._events[0])
        start_time = self.event_queue._events[0].min_start_time
        relative_time =  start_time - self.time_machine.event_seconds_elapsed() - self.preemptive
        self.timer = Timer(max(relative_time, 0.0), self.queue_next_event)
        self.timer.start()
