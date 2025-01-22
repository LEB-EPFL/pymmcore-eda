import datetime, os 
import time
from pathlib import Path
import tensorstore as ts
import shutil
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
unique_log_file = Path(os.path.expanduser(f"~\\AppData\\Local\\pymmcore-plus\\pymmcore-plus\\logs\\pymmcore-plus_{timestamp}.log"))
os.environ['PYMM_LOG_FILE'] = str(unique_log_file)


from pymmcore_plus import CMMCorePlus
from src.pymmcore_eda.actuator import MDAActuator, SmartActuator, ButtonActuator
from src.pymmcore_eda.analyser import Analyser
from src.pymmcore_eda.interpreter import Interpreter
from src.pymmcore_eda.queue_manager import QueueManager
from src.pymmcore_eda.writer import AdaptiveWriter
from useq import Channel, MDASequence

from src.pymmcore_eda.event_hub import EventHub

mmc = CMMCorePlus()
mmc.setDeviceAdapterSearchPaths(
    [*list(mmc.getDeviceAdapterSearchPaths())]
)
mmc.loadSystemConfiguration("C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg")

from smart_scan.custom_engine import CustomEngine
mmc.mda.set_engine(CustomEngine(mmc))

mmc.mda.engine.use_hardware_sequencing = False 

mmc.setProperty("Prime", "Trigger-Expose Out-Mux", 1)
mmc.setProperty("Prime", "ExposeOutMode", "All Rows")
mmc.setChannelGroup("Channel")

mmc.setProperty("pE-800", "Global State", 0)
# mmc.setProperty("pE-800", "SelectionC", 1)
# mmc.setProperty("pE-800", "IntensityC", 10)
# mmc.setProperty('Multi Shutter', 'Physical Shutter 1', 'ZeissReflectedLightShutter')
# mmc.setProperty('Multi Shutter', 'Physical Shutter 2', 'pE-800')
# mmc.setProperty('Core', 'Shutter', 'ZeissTransmittedLightShutter')
# mmc.setProperty('Core', 'Shutter', 'Multi Shutter')
mmc.setConfig("Channel","Brightfield")

mmc.setProperty("pE-800", "Global State", 0)
# mmc.setProperty("pE-800", "SelectionA", 1)
# mmc.setProperty("pE-800", "IntensityA", 10)
# mmc.setProperty('Multi Shutter', 'Physical Shutter 1', 'ZeissReflectedLightShutter')
# mmc.setProperty('Multi Shutter', 'Physical Shutter 2', 'pE-800')
# mmc.setProperty('Core', 'Shutter', 'Multi Shutter')
mmc.setConfig("Channel","DAPI (365nm)")

loc = Path(__file__).parent / "test_data/Cos7_biotrkBlue_3600frames_1s_smart_05.ome.zarr"
writer = AdaptiveWriter(path=loc, delete_existing=True)

hub = EventHub(mmc.mda)
queue_manager = QueueManager()
analyser = Analyser(hub, writer)
interpreter = Interpreter(hub)

mda_sequence = MDASequence(
    channels=(Channel(config="Brightfield",exposure=100),),
    time_plan={"interval": 1, "loops": 3600},
)
mmc.mda._reset_event_timer()
queue_manager.time_machine._t0 = time.perf_counter()

base_actuator = MDAActuator(queue_manager, mda_sequence)
base_actuator.thread.start()
smart_actuator = SmartActuator(queue_manager, hub)
mmc.run_mda(queue_manager.q_iterator, output=writer)
base_actuator.thread.join()
time.sleep(1)
queue_manager.stop_seq()

# time.sleep(10)
# zarr_store = ts.open({
#     "driver": "zarr",
#     "kvstore": {
#         "driver": "file",
#         "path": str(loc), 
#     },
# }).result()
