import time

from pathlib import Path
import tensorstore as ts
import shutil

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
    
    loc = Path(__file__).parent / "test_data/test.ome.zarr"
    writer = AdaptiveWriter(path=loc, delete_existing=True)

    mmc.run_mda(queue_manager.q_iterator, output=writer)
    base_actuator.thread.start()
    time.sleep(1)
    queue_manager.stop_seq()
    time.sleep(1)
    zarr_store = ts.open({
        "driver": "zarr",
        "kvstore": {
            "driver": "file",
            "path": str(loc), 
        },
    }).result()

    # Access data
    data = zarr_store.read().result()
    assert data.shape == (3, 1, 512, 512)

    shutil.rmtree(loc)
    print('removed', loc)

if __name__ == "__main__":
    test_mda()