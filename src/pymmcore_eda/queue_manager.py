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
            event.eda_sequence = self.eda_sequence

        # Offset time
        if event.min_start_time < 0:
            start = self.time_machine.event_seconds_elapsed() + abs(
                event.min_start_time
            )
            event.min_start_time = start

        # Add warmup time
        event.min_start_time += self.warmup

        # if event.index.get("c", 0) != 0:
        #     if len(self.event_register) != 0:
        #         events = self.event_register[event.min_start_time]["events"].copy()
        #         for i, event_i in enumerate(events):
        #             if event_i.index.get('c',0) == event.index.get('c',0):
        #                 del self.event_register[event.min_start_time]['events'][i]
                        
        #                 # if smart scan event, perfom logical or between masks masks:
        #                 try:
        #                     copied_map = event_i.metadata.get('0',0)[0]
        #                     current_map = event.metadata.get('0',0)[0]
        #                     new_map = np.logical_or(copied_map, current_map)
        #                     new_metadata = event.metadata.copy()
        #                     new_metadata['0'][0] = new_map
        #                     event = event.replace(metadata=new_metadata)
        #                 except:
        #                     pass
        
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
        start_time = self.event_queue._events[0].min_start_time if len(self.event_queue._events) > 0 else None
        if start_time is None:
            return
        relative_time =  start_time - self.time_machine.event_seconds_elapsed() - self.preemptive
        self.timer = Timer(max(relative_time, 0.0), self.queue_next_event)
        self.timer.start()
