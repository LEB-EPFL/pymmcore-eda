import time

from _runner import MockRunner


def test_mda():
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence

    from pymmcore_eda.actuator import MDAActuator
    from pymmcore_eda.queue_manager import QueueManager

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    queue_manager = QueueManager()

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 0.1, "loops": 3},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.wait = False

    runner = MockRunner()

    runner.run(queue_manager.q_iterator)
    base_actuator.thread.start()
    time.sleep(1)
    queue_manager.stop_seq()
    assert len(runner.events) == 3
    print(runner.events)
