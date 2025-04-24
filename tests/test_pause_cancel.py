import time

import numpy as np
from pymmcore_plus import CMMCorePlus
from useq import MDASequence

from pymmcore_eda.actuator import MDAActuator
from pymmcore_eda.queue_manager import QueueManager


def test_pause():
    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            "/opt/micro-manager",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration("MMConfig_demo.cfg")
    mmc.mda.engine.use_hardware_sequencing = False

    queue_manager = QueueManager(mmc)

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 0.2, "loops": 30},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.wait = False

    # Get the frameReadys and store them
    events = []
    metas = []

    def receive_frame_ready(frame, event, meta):
        events.append(event)
        metas.append(meta)

    mmc.mda.events.frameReady.connect(receive_frame_ready)

    mmc.run_mda(queue_manager.acq_queue_iterator)
    base_actuator.thread.start()
    base_actuator.thread.join()
    time.sleep(4)
    mmc.mda.toggle_pause()
    time.sleep(2)
    mmc.mda.toggle_pause()
    time.sleep(2)
    queue_manager.stop_seq()

    times = [meta["runner_time_ms"] for meta in metas]
    diffs = np.diff(times)
    print(diffs)
    diffs = diffs[1:]
    assert min(diffs) > 150
    assert min(diffs) < 210
    assert max(diffs) > 2100
    assert max(diffs) < 2300


def test_cancel():
    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            "/opt/micro-manager",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration("MMConfig_demo.cfg")
    mmc.mda.engine.use_hardware_sequencing = False

    queue_manager = QueueManager(mmc)

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 0.2, "loops": 20},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.wait = False

    mmc.run_mda(queue_manager.acq_queue_iterator)
    base_actuator.thread.start()
    time.sleep(5)
    mmc.mda.cancel()
    time.sleep(1)


if __name__ == "__main__":
    # test_pause()
    test_cancel()
