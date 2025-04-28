import logging
import time

from pymmcore_plus import CMMCorePlus
from pymmcore_plus._logger import logger
from useq import Channel, MDASequence

from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda.actuator import Actuator, MDAActuator
from pymmcore_eda.analyser import Analyser
from pymmcore_eda.event_hub import EventHub
from pymmcore_eda.interpreter import Interpreter
from pymmcore_eda.queue_manager import QueueManager

for handler in list(logger.handlers):
    if isinstance(handler, logging.handlers.RotatingFileHandler):
        logger.removeHandler(handler)

mmc = CMMCorePlus()
try:
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Users/stepp/AppData/Local/pymmcore-plus/pymmcore-plus/mm/Micro-Manager_2.0.3_20240618"
        ]
    )
    mmc.loadSystemConfiguration("C:/Control_2/240715_ZeissAxioObserver7.cfg")
    MY_CHANNELS = ("Brightfield", "Cy5 (635nm)", "GFP (470nm)")
except OSError:
    mmc.loadSystemConfiguration()
    MY_CHANNELS = ("Cy5", "DAPI", "FITC")
print("Loaded system configuration")

mmc.mda.engine.use_hardware_sequencing = False
print("Loaded system configuration")

event_hub = EventHub(mmc.mda)
eda_sequence = EDASequence(channels=MY_CHANNELS)
queue_manager = QueueManager(eda_sequence=eda_sequence)

# Create an MDA sequence with a Cy5 channel and time plan
mda_sequence = MDASequence(
    channels=(Channel(config=MY_CHANNELS[0], exposure=100),),
    time_plan={"interval": 1, "loops": 30},
)


base_actuator = MDAActuator(queue_manager, mda_sequence)
base_actuator.wait = False
base_actuator.thread.start()

analyser = Analyser(hub=event_hub, prediction_time=0.05)
interpreter = Interpreter(event_hub, smart_event_period=7)
smart_actuator = Actuator(queue_manager, event_hub, n_events=2)
smart_actuator.channel_name = MY_CHANNELS[1]

mmc.run_mda(queue_manager.acq_queue_iterator)
time.sleep(35)
queue_manager.stop_seq()
