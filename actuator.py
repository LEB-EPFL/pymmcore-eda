from queue import Queue
from useq import MDAEvent

class Actuator():
    def __init__(self, queue: Queue, sentinel: object):
        self.queue = queue
        self.sentinel = sentinel

    def run(self):
        t = 0
        t_max = 100 
        while t < t_max:
            if self.queue.empty():
                event = MDAEvent(channel="phase", index = {"t": t}, min_start_time=t)
                self.queue.put(event)
                t += 1



if __name__ == "__main__":
    from pymmcore_plus import CMMCorePlus
    mmc = CMMCorePlus()

    
    q = Queue()                    # create the queue
    STOP = object()                # any object can serve as the sentinel
    q_iterator = iter(q.get, STOP) # create the queue-backed iterable
    actuator = Actuator(q, STOP)   # create the producer
    actuator.run()                 # start 

    # start the acquisition in a separate thread
    mmc.run_mda(q_iterator)
        
    print(q.get())
