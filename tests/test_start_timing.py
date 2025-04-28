import time

import numpy as np
from pymmcore_plus import CMMCorePlus
from useq import MDASequence

from pymmcore_eda.actuator import MDAActuator
from pymmcore_eda.queue_manager import QueueManager


def test_start_times():
    mmc = CMMCorePlus()
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    queue_manager = QueueManager(mmcore=mmc)

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 0.2, "loops": 20},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.wait = False

    events = []
    metas = []

    def receive_frame_ready(frame, event, meta):
        events.append(event)
        metas.append(meta)

    mmc.mda.events.frameReady.connect(receive_frame_ready)

    mmc.run_mda(queue_manager.acq_queue_iterator)
    base_actuator.thread.start()
    base_actuator.thread.join()

    time.sleep(10)
    queue_manager.stop_seq()

    times = [meta["runner_time_ms"] for meta in metas]
    print(times)
    diffs = np.diff(times)
    print(diffs)
    assert diffs[0] > 190
    assert diffs[0] < 210


if __name__ == "__main__":
    test_start_times()
