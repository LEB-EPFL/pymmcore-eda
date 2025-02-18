import datetime, os 
import time
from pathlib import Path
import tensorstore as ts
import shutil
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
unique_log_file = Path(os.path.expanduser(f"~\\AppData\\Local\\pymmcore-plus\\pymmcore-plus\\logs\\pymmcore-plus_{timestamp}.log"))
os.environ['PYMM_LOG_FILE'] = str(unique_log_file)


from pymmcore_plus import CMMCorePlus

from src.pymmcore_eda.actuator import MDAActuator, ButtonActuator, SmartActuator_widefield
from src.pymmcore_eda.analyser import Analyser, Dummy_Analyser
from src.pymmcore_eda.interpreter import Interpreter_widefield
from src.pymmcore_eda.queue_manager import QueueManager
from src.pymmcore_eda.writer import AdaptiveWriter
from src.pymmcore_eda.writer import AdaptiveWriter
from src.pymmcore_eda.event_hub import EventHub

from smart_scan.smart_actuator_scan import SmartActuator_scan
from smart_scan.interpreter_scan import Interpreter_scan

from useq import Channel, MDASequence
from pathlib import Path

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

loc = Path(__file__).parent / "test_data/Cos7_MTDeepRed_200frames_1s_widefield_07_tresh_08.ome.zarr"
writer = AdaptiveWriter(path=loc, delete_existing=True)


hub = EventHub(mmc.mda, writer=writer)

queue_manager = QueueManager()

# analyser = Dummy_Analyser(hub)
analyser = Analyser(hub)

# define the MDA sequence
mda_sequence = MDASequence(
    channels=(Channel(config="Brightfield",exposure=100),),
    time_plan={"interval": 1, "loops": 200},
)
mmc.mda._reset_event_timer()
queue_manager.time_machine._t0 = time.perf_counter()

# initialise all the components
base_actuator = MDAActuator(queue_manager, mda_sequence)

# for smart widefield events
interpreter = Interpreter_widefield(hub)
smart_actuator = SmartActuator_widefield(queue_manager, hub, n_events=20)

# for smart scan events
# interpreter = Interpreter_scan(hub)
# smart_actuator = SmartActuator_scan(queue_manager, hub, n_events=5)


base_actuator.thread.start()
mmc.run_mda(queue_manager.q_iterator, output = writer)

base_actuator.thread.join()
time.sleep(1)
queue_manager.stop_seq()

