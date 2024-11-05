from queue import Queue
from useq import MDAEvent, MDASequence
from threading import Thread
import time
from pymmcore_plus._logger import logger
from queue_manager import QueueManager



class Actuator():
    def __init__(self, queue: Queue, sentinel: object):
        self.queue = queue
        self.sentinel = sentinel

        self.thread = Thread(target=self.run)
        self.event = "dumb"

    def run(self):
        t = 0
        t_max = 20
        while t < t_max:
            if self.queue.empty():
                event = MDAEvent(index={"t": t, "c": 0}, min_start_time=t)
                self.queue.put(event)
                if t % 5 == 0:
                    event = MDAEvent(channel=self.event, index={
                                     "t": t, "c": 1}, min_start_time=t)
                    self.queue.put(event)
                t += 1
        self.queue.put(self.sentinel)

class BaseActuator():
    def __init__(self, queue_manager: QueueManager, mda_sequence: MDASequence):
        self.queue_manager = queue_manager
        self.mda_sequence = mda_sequence
        self.thread = Thread(target=self.run)

    def run(self):
        for event in self.mda_sequence:
            self.queue_manager.register_event(event)

class DumbActuator():
    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager
        self.thread = Thread(target=self.run)
        self.event = "dumb"

    def run(self):
        t_ind = 0
        t = 0
        t_max = 20
        while t <= t_max:
            if t % 5 == 0:
                event = MDAEvent(index={"t": t_ind, "c": 1}, min_start_time=t)
                self.queue_manager.register_event(event)
                t_ind += 1
            t += 2  

if __name__ == "__main__":
    from pymmcore_plus import CMMCorePlus
    from queue_manager import QueueManager
    from time_machine import TimeMachine

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        ["C:/Program Files/Micro-Manager-2.0/"] + list(mmc.getDeviceAdapterSearchPaths()))
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    mda_sequence = MDASequence(
        channels= ['DAPI'],
        time_plan={"interval": 2, "loops": 11},)
    queue_manager = QueueManager(TimeMachine())
    actuator = BaseActuator(queue_manager, mda_sequence)   # create the producer
    d_actuator = DumbActuator(queue_manager)

    # start the acquisition in a separate thread
    mda_thread = mmc.run_mda(queue_manager.q_iterator)
    time.sleep(1)
    actuator.thread.start()
    d_actuator.thread.start()
    actuator.thread.join()
    time.sleep(30)
    queue_manager.stop_seq()
    mda_thread.join()
