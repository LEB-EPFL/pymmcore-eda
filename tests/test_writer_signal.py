import time

from pathlib import Path
import tensorstore as ts
import shutil
import sys
sys.path.append(str(Path(__file__).parent.parent))


def test_mda():
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence

    from pymmcore_eda.actuator import MDAActuator, ButtonActuator
    from pymmcore_eda.queue_manager import QueueManager
    from pymmcore_eda.writer import AdaptiveWriter
    from pymmcore_eda.event_hub import EventHub
    from pymmcore_eda.analyser import Dummy_Analyser
    from pymmcore_eda.interpreter import Interpreter_widefield
    from useq import Channel

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    mmc.setProperty("Camera", "OnCameraCCDXSize", 2048)
    mmc.setProperty("Camera", "OnCameraCCDYSize", 2048)

    mda_sequence = MDASequence(
        channels=["DAPI"],
        time_plan={"interval": 0.1, "loops": 3},
    )
   
    loc = Path(__file__).parent / "test_data/test.ome.zarr"
    writer = AdaptiveWriter(path=loc, delete_existing=True)
    writer.reshape_on_finished = False

    hub = EventHub(mmc.mda, writer)
    queue_manager = QueueManager()


    mda_sequence = MDASequence(
        channels=(Channel(config="DAPI",exposure=100),),
        time_plan={"interval": 1, "loops": 5},
    )
    mmc.mda._reset_event_timer()
    queue_manager.time_machine._t0 = time.perf_counter()

    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.thread.start()
    smart_actuator = ButtonActuator(queue_manager)
    mmc.run_mda(queue_manager.q_iterator, output=writer)
    base_actuator.thread.join()
    time.sleep(5)
    queue_manager.stop_seq()
    time.sleep(5)

    zarr_store = ts.open({
        "driver": "zarr",
        "kvstore": {
            "driver": "file",
            "path": str(loc), 
        },
    }).result()

    # Access data
    data = zarr_store.read().result()
    print(data.shape)
    assert data.shape == (300, 512, 512)

    shutil.rmtree(loc)
    print('removed', loc)

if __name__ == "__main__":
    test_mda()