import shutil
import sys
import time
from pathlib import Path

import tensorstore as ts

sys.path.append(str(Path(__file__).parent.parent))


def test_mda():
    from pymmcore_plus import CMMCorePlus
    from useq import Channel, MDASequence

    from pymmcore_eda.actuator import ButtonActuator, MDAActuator
    from pymmcore_eda.event_hub import EventHub
    from pymmcore_eda.queue_manager import QueueManager
    from pymmcore_eda.writer import AdaptiveWriter

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            "/opt/micro-manager",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    mmc.setProperty("Camera", "OnCameraCCDXSize", 512)
    mmc.setProperty("Camera", "OnCameraCCDYSize", 512)

    loc = Path(__file__).parent / "test_data/test.ome.zarr"
    writer = AdaptiveWriter(path=loc, delete_existing=True)
    writer.reshape_on_finished = True

    EventHub(mmc.mda, writer)
    queue_manager = QueueManager(time_machine=mmc.mda)

    mda_sequence = MDASequence(
        channels=(Channel(config="DAPI", exposure=100),),
        time_plan={"interval": 0.5, "loops": 5},
    )

    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.thread.start()
    ButtonActuator(queue_manager)
    mmc.run_mda(queue_manager.acq_queue_iterator, output=writer)
    base_actuator.thread.join()
    time.sleep(2)
    queue_manager.stop_seq()
    time.sleep(1.5)
    zarr_store = ts.open(
        {
            "driver": "zarr",
            "kvstore": {
                "driver": "file",
                "path": str(loc),
            },
        }
    ).result()

    # Access data
    data = zarr_store.read().result()
    print(data.shape)
    assert data.shape == (1, 5, 512, 512)

    shutil.rmtree(loc)
    print("removed", loc)


if __name__ == "__main__":
    test_mda()
