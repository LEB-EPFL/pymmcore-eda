from queue import Queue
from useq import MDAEvent
from threading import Thread
import time
from pymmcore_plus._logger import logger


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


if __name__ == "__main__":
    from pymmcore_plus import CMMCorePlus

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        ["C:/Program Files/Micro-Manager-2.0/"] + list(mmc.getDeviceAdapterSearchPaths()))
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    q = Queue()                    # create the queue
    STOP = object()                # any object can serve as the sentinel
    q_iterator = iter(q.get, STOP)  # create the queue-backed iterable
    actuator = Actuator(q, STOP)   # create the producer

    # start the acquisition in a separate thread
    mda_thread = mmc.run_mda(q_iterator)
    time.sleep(1)
    actuator.thread.start()
    time.sleep(10)
    actuator.event = "smart"
    actuator.thread.join()
    mda_thread.join()
