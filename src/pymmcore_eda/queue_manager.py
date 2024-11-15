
from __future__ import annotations

from queue import Queue
from threading import Timer
from typing import TYPE_CHECKING

from pymmcore_eda.time_machine import TimeMachine

if TYPE_CHECKING:
    from useq import MDAEvent


class QueueManager:
    """Component responsible to manage events and their timing in front of the Queue.

    Closer description in structure.md.
    """

    def __init__(self, time_machine: TimeMachine | None = None):
        self.q = Queue()
        self.stop = object()
        self.q_iterator = iter(self.q.get, self.stop)
        self.time_machine = time_machine or TimeMachine()
        self.event_register = {}
        self.preemptive = 0.02
        self.t_idx = 0
        # self.axis_order = 'tpgcz' we might need this

    def register_actuator(self, actuator):
        """Actuator asks for indices for example which channel to push to."""
        pass

    def register_event(self, event):
        """Actuators call this to request an event to be put on the event_register."""
        # Offset index
        if event.index.get('t', 0) < 0:
            keys = list(self.event_register.keys())
            start = 0 if len(keys) == 0 else min(keys)
            event = event.replace(min_start_time=start)

        # Offset time
        if event.min_start_time < 0:
            start = (self.time_machine.event_seconds_elapsed() +
                    abs(event.min_start_time))
            event = event.replace(min_start_time=start)

        if event.min_start_time not in self.event_register.keys():
            self.event_register[event.min_start_time] = {'timer': None, 'events': []}

        self.event_register[event.min_start_time]['events'].append(event)
        if self.event_register[event.min_start_time]['timer'] is None:
            self._set_timer_for_event(event)

    def queue_events(self, start_time: float):
        """Put events on the queue that are due to be acquired.

        Just before the actual acquisition time, put the event on the queue
        that exposes them to the pymmcore-plus runner.
        """
        events = self.event_register[start_time]['events'].copy()
        events = sorted(events, key= lambda event:(event.index.get('c', 100)))
        for idx, event in enumerate(events):
            new_index = event.index.copy()
            new_index['t'] = self.t_idx
            event = event.replace(index=new_index)
            self.q.put(event)

            # If this event reset the event_timer in the Runner, we have to reset the
            # time_machine and update the timers for all queued events.
            if event.reset_event_timer and idx == 0: # idx > 0 gets more complicated
                self.time_machine.consume_event(event)
                old_items = list(self.event_register.items())
                for key, value in old_items:
                    if key == start_time:
                        continue
                    self._set_timer_for_event(value['events'][0])


        self.t_idx += 1
        del self.event_register[start_time]

    def stop_seq(self):
        """Stop the sequence after the events currently on the queue."""
        self.q.put(self.stop)

    def _set_timer_for_event(self, event: MDAEvent):
        """Set or reset the timer for an event."""
        if self.event_register[event.min_start_time]['timer']:
            self.event_register[event.min_start_time]['timer'].cancel()
        if event.min_start_time:
            time_until_start = (event.min_start_time -
                                self.time_machine.event_seconds_elapsed()
                                - self.preemptive)
        else:
            time_until_start = -1
        time_until_start = max(0, time_until_start)
        self.event_register[event.min_start_time]['timer'] = Timer(time_until_start,
                                                                       self.queue_events,
                                                                       args=[event.min_start_time])
        self.event_register[event.min_start_time]['timer'].start()
