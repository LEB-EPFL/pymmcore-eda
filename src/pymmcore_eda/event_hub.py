from pymmcore_plus.mda import MDARunner
import numpy as np
from useq import MDAEvent
from psygnal import Signal, SignalGroup

class EventHub(SignalGroup):
    frameReady = Signal(np.ndarray, MDAEvent, dict)

    new_analysis = Signal(np.ndarray, MDAEvent, dict)
    new_interpretation = Signal(int, MDAEvent, dict)
    def __init__(self, runner: MDARunner) -> None:
        self.runner = runner
        self.runner.events.frameReady.connect(self.frameReady.emit)


if __name__ == "__main__":  
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence
    from analyser import Analyser
    from interpreter import Interpreter
    from actuator import SmartActuator, BaseActuator
    from queue_manager import QueueManager
    import time
    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        ["C:/Program Files/Micro-Manager-2.0/"] + list(mmc.getDeviceAdapterSearchPaths()))
    mmc.loadSystemConfiguration()
    
    hub = EventHub(mmc.mda)
    queue_manager = QueueManager()

    analyser = Analyser(hub)
    interpreter = Interpreter(hub)
    mda_sequence = MDASequence(
        channels= ['DAPI'],
        time_plan={"interval": 3, "loops": 11},)
    base_actuator = BaseActuator(queue_manager, mda_sequence)
    smart_actuator = SmartActuator(queue_manager, hub)
    
    mmc.run_mda(queue_manager.q_iterator)
    base_actuator.thread.start()
    base_actuator.thread.join()
    time.sleep(30)
    queue_manager.stop_seq()