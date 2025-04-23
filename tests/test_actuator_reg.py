import time

from _runner import MockRunner


def test_actuator_reg():
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence

    from pymmcore_eda._eda_sequence import EDASequence
    from pymmcore_eda.actuator import MDAActuator
    from pymmcore_eda.queue_manager import QueueManager

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration("MMConfig_demo.cfg")
    mmc.mda.engine.use_hardware_sequencing = False

    eda_sequence = EDASequence(channels=("DAPI", "Cy5"))
    queue_manager = QueueManager(eda_sequence=eda_sequence)

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 1, "loops": 3},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)

    mda_sequence2 = MDASequence(
        channels=["Cy5"],
        time_plan={"interval": 1, "loops": 3},
    )
    base_actuator2 = MDAActuator(queue_manager, mda_sequence2)

    runner = MockRunner()

    base_actuator.thread.start()
    time.sleep(1)
    base_actuator2.thread.start()
    time.sleep(1)
    # mmc.run_mda(queue_manager.q_iterator)
    runner.run(queue_manager.acq_queue_iterator)
    time.sleep(7)
    queue_manager.stop_seq()
    time.sleep(1)
    assert len(runner.events) == 6
    assert runner._axis_max["c"] == 1
    assert runner.events[0].channel.config == "DAPI"
    assert runner._axis_max["t"] == 2


def test_double_reg():
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence

    from pymmcore_eda._eda_sequence import EDASequence
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

    eda_sequence = EDASequence(channels=("DAPI", "Cy5"))
    queue_manager = QueueManager(eda_sequence=eda_sequence)

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 1, "loops": 3},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)

    mda_sequence2 = MDASequence(
        channels=["Cy5", "DAPI"],
        time_plan={"interval": 1, "loops": 3},
    )
    base_actuator2 = MDAActuator(queue_manager, mda_sequence2)

    runner = MockRunner(stop=queue_manager.stop)

    base_actuator2.thread.start()
    time.sleep(1)
    base_actuator.thread.start()
    time.sleep(1)
    # mmc.run_mda(queue_manager.q_iterator)
    runner.run(queue_manager.acq_queue_iterator)
    time.sleep(6)
    queue_manager.stop_seq()
    time.sleep(1)
    assert len(runner.events) == 6
    assert runner._axis_max["c"] == 1
    assert runner.events[0].channel.config == "DAPI"
    assert runner._axis_max["t"] == 2


if __name__ == "__main__":
    test_double_reg()
