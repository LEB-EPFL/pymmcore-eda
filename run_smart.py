# import datetime, os 
# from pathlib import Path
# timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
# unique_log_file = Path(os.path.expanduser(f"~\\AppData\\Local\\pymmcore-plus\\pymmcore-plus\\logs\\pymmcore-plus_{timestamp}.log"))
# os.environ['PYMM_LOG_FILE'] = str(unique_log_file)
from pymmcore_plus import CMMCorePlus
from pymmcore_eda.actuator import MDAActuator, SmartActuator, ButtonActuator
from pymmcore_eda.analyser import Analyser
from pymmcore_eda.interpreter import Interpreter
from pymmcore_eda.queue_manager import QueueManager
from useq import Channel, MDASequence

from pymmcore_eda.event_hub import EventHub

mmc = CMMCorePlus()
mmc.setDeviceAdapterSearchPaths(
    ["C:/Program Files/Micro-Manager-2.0/", *list(mmc.getDeviceAdapterSearchPaths())]
)
mmc.loadSystemConfiguration()
mmc.mda.engine.use_hardware_sequencing = False


hub = EventHub(mmc.mda)
queue_manager = QueueManager()

analyser = Analyser(hub)
interpreter = Interpreter(hub)
mda_sequence = MDASequence(
    channels=(Channel(config="GFP (470nm)",exposure=10),),
    time_plan={"interval": 3, "loops": 10},
)
base_actuator = MDAActuator(queue_manager, mda_sequence)
smart_actuator = SmartActuator(queue_manager, hub)

mmc.run_mda(queue_manager.q_iterator)
base_actuator.thread.start()
base_actuator.thread.join()
queue_manager.stop_seq()
