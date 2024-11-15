
from __future__ import annotations
from queue import Queue

from time_machine import TimeMachine
from threading import Timer
from useq import MDAEvent
import time
from _logger import logger


class QueueManager():
    """ Component responsible to manage events and their timing in front of the Queue.

    Closer description in structure.md.
    """
    def __init__(self, time_machine: TimeMachine | None = None):
        self.q = Queue()                    # create the queue
        self.stop = object()                # any object can serve as the sentinel
        self.q_iterator = iter(self.q.get, self.stop)  # create the queue-backed iterable
        self.time_machine = time_machine or TimeMachine()
        self.event_register = {}
        self.preemptive = 0.02
        self.t_idx = 0
        # self.axis_order = 'tpgcz' we might need this

    def register_actuator(self, actuator):
        """Actuator asks for its base indices for example which channel its allowed to push to"""
        pass

    def register_event(self, event):
        "Actuators call this to request an event to be put on the event_register."
        if event.index.get('t', 0) < 0:
            event = event.replace(min_start_time= min(list(self.event_register.keys()) + [0.0]))

        if not event.min_start_time in self.event_register.keys():
            self.event_register[event.min_start_time] = {'timer': None, 'events': []}
        
        self.event_register[event.min_start_time]['events'].append(event)
        if self.event_register[event.min_start_time]['timer'] is None:
            self._set_timer_for_event(event)

    def queue_events(self, start_time: float):
        """Just before the actual acquisition time, put the event on the queue that exposes them to the pymmcore-plus runner."""
        events = self.event_register[start_time]['events'].copy()
        events = sorted(events, key= lambda event:(event.index.get('c', 100)))
        for idx, event in enumerate(events):
            new_index = event.index.copy()
            new_index['t'] = self.t_idx
            event = event.replace(index=new_index)
            self.q.put(event)
        
            # If this event reset the event_timer in the Runner, we have to reset the time_machine and update the timers for all queued events.
            if event.reset_event_timer and idx == 0: # if not idx == 0 gets more complicated
                self.time_machine.consume_event(event)
                old_items = list(self.event_register.items())
                for key, value in old_items:
                    if key == start_time:
                        continue
                    self._set_timer_for_event(value['events'][0])

        
        self.t_idx += 1
        del self.event_register[start_time]

    def stop_seq(self):
        self.q.put(self.stop)
    
    def _set_timer_for_event(self, event: MDAEvent):
        """Set or reset the timer for an event"""
        if self.event_register[event.min_start_time]['timer']:
            self.event_register[event.min_start_time]['timer'].cancel()
        if event.min_start_time:
            time_until_start = event.min_start_time - self.time_machine.event_seconds_elapsed() - self.preemptive
        else:
            time_until_start = -1
        time_until_start = max(0, time_until_start)
        self.event_register[event.min_start_time]['timer'] = Timer(time_until_start, 
                                                                       self.queue_events,
                                                                       args=[event.min_start_time])
        self.event_register[event.min_start_time]['timer'].start()


if __name__ == "__main__":
    from useq import MDASequence, MDAEvent
    from pymmcore_plus import CMMCorePlus
    from operator import attrgetter
    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        ["C:/Program Files/Micro-Manager-2.0/"] + list(mmc.getDeviceAdapterSearchPaths()))
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False
        

    events = [MDAEvent(index={'t': 0, 'c': 0, 'z': 0, 'g': 0}),
              MDAEvent(index={'t': 0, 'c': 0, 'z': 1, 'g': 0}),
              MDAEvent(index={'t': 0, 'c': 1, 'z': 0, 'g': 0}),
              MDAEvent(index={'t': 0, 'c': 1, 'z': 1, 'g': 0}),
              MDAEvent(index={'t': 0, 'c': 0, 'z': 0, 'g': 1}),
              MDAEvent(index={'t': 0, 'c': 0, 'z': 1, 'g': 1}),
              MDAEvent(index={'t': 0, 'c': 1, 'z': 0, 'g': 1}),
              MDAEvent(index={'t': 0, 'c': 1, 'z': 1, 'g': 1}),]

    sort = sorted(events, key=lambda event:event.index['c'])
    sort = [str(x) for x in sort]
    print('\n'.join(sort))
    print('----')

    sort = sorted(events, key=lambda event:event.index['z'])
    sort = [str(x) for x in sort]
    print('\n'.join(sort))
    print('----')
    
    sort = sorted(events, key= lambda event:(event.index['z'], event.index['g'], event.index['c']))
    sort = [str(x) for x in sort]
    print('\n'.join(sort))
    print('----')

    sort = sorted(events, key= lambda event:(event.index['g'], event.index['z'], event.index['c']))
    sort = [str(x) for x in sort]
    print('\n'.join(sort))


