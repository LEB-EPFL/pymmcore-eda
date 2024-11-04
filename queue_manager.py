
from queue import Queue

from time_machine import TimeMachine


class QueueManager():
    def __init__(self, queue: Queue | None, time_machine: TimeMachine):
        self.queue = queue or Queue()
        self.time_machine = time_machine
        self.event_register = {}
        # self.axis_order = 'tpgcz' we might need this

    def register_actuator(self, actuator):
        "Actuator asks for its base indices for example which channel its allowed to push to"
        pass

    def register_event(self, event):
        if not event.min_start_time in self.event_register.keys():
            self.event_register[event.min_start_time] = []

        # Now consider where this event should go. z stack before channel or after for example?
        self.event_register[event.min_start_time].append(event)

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


