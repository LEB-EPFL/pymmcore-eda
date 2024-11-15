from __future__ import annotations
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from useq import MDAEvent


class TimeMachine():
    """Component to syncronize time between the Runner in pymmcore-plus and the QueueManager.
    
    This avoids having direct connections between the two components. Like this seems to be accurate enough (10ms).
    """
    def __init__(self):
        self._t0 = time.perf_counter()

    def consume_event(self, event: MDAEvent):
        if event.reset_event_timer:
            self._t0 = time.perf_counter()

    def event_seconds_elapsed(self, *_) -> float:
        return time.perf_counter() - self._t0



if __name__ == "__main__":
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence
    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        ["C:/Program Files/Micro-Manager-2.0/"] + list(mmc.getDeviceAdapterSearchPaths()))
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False


    tm = TimeMachine()


    seq = MDASequence(
        axis_order='pt',
        stage_positions = [(0,0), (1,1)],
        time_plan= {"interval": 2, "loops": 5})
    
    mmc.mda.events.eventStarted.connect(tm.consume_event)
    mmc.mda.events.eventStarted.connect(tm.event_seconds_elapsed)

    mmc.run_mda(seq, block=True)
