import shutil
import sys
import time
from pathlib import Path

import tensorstore as ts

sys.path.append(str(Path(__file__).parent.parent))


def test_mda():
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence

    from pymmcore_eda.actuator import MDAActuator
    from pymmcore_eda.queue_manager import QueueManager
    from pymmcore_eda.writer import AdaptiveWriter

    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            "/opt/micro-manager/lib/micro-manager",
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

    loc = Path(__file__).parent / "test_data/test.ome.zarr"
    writer = AdaptiveWriter(path=loc, delete_existing=True)

    mmc.run_mda(queue_manager.acq_queue_iterator, output=writer)
    base_actuator.thread.start()
    base_actuator.thread.join()
    queue_manager.stop_seq()
    time.sleep(3)
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
    assert data.shape == (1, 3, 512, 512)

    shutil.rmtree(loc)
    print("removed", loc)


if __name__ == "__main__":
    test_mda()
