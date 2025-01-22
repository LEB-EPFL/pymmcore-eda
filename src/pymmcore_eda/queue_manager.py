from __future__ import annotations

from queue import Queue
from threading import Timer
from typing import TYPE_CHECKING
import numpy as np

from src.pymmcore_eda.time_machine import TimeMachine

if TYPE_CHECKING:
    from useq import MDAEvent


class QueueManager:
    """Component responsible to manage events and their timing in front of the Queue.

    Closer description in structure.md.
    """

    def __init__(self, time_machine: TimeMachine | None = None):
        self.q: Queue = Queue()
        self.stop = object()
        self.q_iterator = iter(self.q.get, self.stop)
        self.time_machine = time_machine or TimeMachine()
        self.event_register: dict = {}
        self.preemptive = 0.02
        self.t_idx = 0

        self._axis_max: dict[str, int] = {}
        # self.axis_order = 'tpgcz' we might need this

    def register_actuator(self, actuator, n_channels: int = 1):
        """Actuator asks for indices for example which channel to push to."""
        self._axis_max['c'] = self._axis_max.get('c', 0) + n_channels
        return list(range(self._axis_max['c']-n_channels, self._axis_max['c']))

    def register_event(self, event):
        """Actuators call this to request an event to be put on the event_register."""
        
        # Offset index
        if event.index.get("t", 0) < 0:
            keys = list(self.event_register.keys())
            keys = sorted(keys)
            if len(keys) == 0:
                start = 0
            elif abs(event.index.get("t", 0)) > len(keys):
                start = keys[-1]
            else:
                start = keys[abs(event.index.get("t", 0))-1]
            
            event = event.replace(min_start_time=start)

        # Offset time
        if event.min_start_time < 0:
            start = self.time_machine.event_seconds_elapsed() + abs(
                event.min_start_time
            )
            event = event.replace(min_start_time=start)

        # "summing" masks:
        if event.index.get("c", 0) != 0:
            if len(self.event_register) != 0:
                events = self.event_register[event.min_start_time]["events"].copy()
                for i, event_i in enumerate(events):
                    if event_i.index.get('c',0) == event.index.get('c',0):
                        copied_map = event_i.metadata.get('0',0)[0]
                        current_map = event.metadata.get('0',0)[0]
                        new_map = np.logical_or(copied_map, current_map)
                        new_metadata = event.metadata.copy()
                        new_metadata['0'][0] = new_map
                        event = event.replace(metadata=new_metadata)
                        del self.event_register[event.min_start_time]['events'][i]
        
        if event.min_start_time not in self.event_register.keys():
            self.event_register[event.min_start_time] = {"timer": None, "events": []}

        self.event_register[event.min_start_time]["events"].append(event)
        if self.event_register[event.min_start_time]["timer"] is None:
            self._set_timer_for_event(event)

        for k, v in event.index.items():
            self._axis_max[k] = max(self._axis_max.get(k, 0), v)

    def queue_events(self, start_time: float):
        """Put events on the queue that are due to be acquired.

        Just before the actual acquisition time, put the event on the queue
        that exposes them to the pymmcore-plus runner.
        """
        events = self.event_register[start_time]["events"].copy()
        events = sorted(events, key=lambda event: (event.index.get("c", 100)))
        for idx, event in enumerate(events):
            new_index = event.index.copy()
            new_index["t"] = self.t_idx
            event = event.replace(index=new_index)
            self.q.put(event)

            # If this event reset the event_timer in the Runner, we have to reset the
            # time_machine and update the timers for all queued events.
            if event.reset_event_timer and idx == 0:  # idx > 0 gets more complicated
                self.time_machine.consume_event(event)
                old_items = list(self.event_register.items())
                for key, value in old_items:
                    if key == start_time:
                        continue
                    self._set_timer_for_event(value["events"][0])

        self.t_idx += 1
        del self.event_register[start_time]

    def stop_seq(self):
        """Stop the sequence after the events currently on the queue."""
        self.q.put(self.stop)

    def _set_timer_for_event(self, event: MDAEvent):
        """Set or reset the timer for an event."""
        #If we are the time 0 event and we reset, wait for potential other events to be queued
        if all([event.min_start_time == 0,
               event.reset_event_timer,
               self.event_register[event.min_start_time]["timer"] is None]): 
            self.event_register[event.min_start_time]["timer"] = False
            Timer(0.005, self._set_timer_for_event, args=[event]).start()
            return
        if self.event_register[event.min_start_time]["timer"]:
            self.event_register[event.min_start_time]["timer"].cancel()
        if event.min_start_time:
            time_until_start = (
                event.min_start_time
                - self.time_machine.event_seconds_elapsed()
                - self.preemptive
            )
        else:
            time_until_start = -1
        time_until_start = max(0, time_until_start)
        self.event_register[event.min_start_time]["timer"] = Timer(
            time_until_start, self.queue_events, args=[event.min_start_time]
        )
        self.event_register[event.min_start_time]["timer"].start()
