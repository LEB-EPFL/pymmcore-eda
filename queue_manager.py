
from queue import Queue

from time_machine import TimeMachine
from threading import Timer
from useq import MDAEvent
import time

class QueueManager():
    def __init__(self, time_machine: TimeMachine | None = None):
        self.q = Queue()                    # create the queue
        self.stop = object()                # any object can serve as the sentinel
        self.q_iterator = iter(self.q.get, self.stop)  # create the queue-backed iterable
        self.time_machine = time_machine or TimeMachine()
        self.event_register = {}
        self.preemptive = 0.01
        self.t_idx = 0
        # self.axis_order = 'tpgcz' we might need this

    def register_actuator(self, actuator):
        "Actuator asks for its base indices for example which channel its allowed to push to"
        pass

    def register_event(self, event):
        if not event.min_start_time in self.event_register.keys():
            self.event_register[event.min_start_time] = {'timer': None, 'events': []}

        self.event_register[event.min_start_time]['events'].append(event)
        if self.event_register[event.min_start_time]['timer'] is None:
            self._set_timer_for_event(event)

    def queue_events(self, start_time: float):
        events = self.event_register[start_time]['events'].copy()
        events = sorted(events, key= lambda event:(event.index.get('c', 100)))
        for event in events:
            new_index = event.index.copy()
            new_index['t'] = self.t_idx
            event = event.replace(index=new_index)
            self.q.put(event)
        time.sleep(self.preemptive)
        for event in events:
            self.time_machine.consume_event(event)
        self.t_idx += 1
        del self.event_register[start_time]

    def stop_seq(self):
        self.q.put(self.stop)
    
    def _set_timer_for_event(self, event: MDAEvent):
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


