import time

from pymmcore_plus import CMMCorePlus
from useq import MDASequence

from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda.actuator import MDAActuator
from pymmcore_eda.queue_manager import QueueManager

mmc = CMMCorePlus()
try:
    mmc.setDeviceAdapterSearchPaths(["C:/Users/stepp/AppData/Local/pymmcore-plus/pymmcore-plus/mm/Micro-Manager_2.0.3_20240618"])
    mmc.loadSystemConfiguration("C:/Control_2/240715_ZeissAxioObserver7.cfg")
    MY_CHANNELS = ("Brightfield", "Cy5 (635nm)", "GFP (470nm)")
except OSError:
    mmc.loadSystemConfiguration()
    MY_CHANNELS = ("Cy5", "DAPI", "FITC")
print("Loaded system configuration")
mmc.mda.engine.use_hardware_sequencing = False

eda_sequence = EDASequence()
queue_manager = QueueManager(eda_sequence=eda_sequence, mmcore=mmc)
queue_manager.warmup = 3

mda_sequence = MDASequence(
    channels=[MY_CHANNELS[1]],
    time_plan={"interval": 1, "loops": 5},
)
base_actuator = MDAActuator(queue_manager, mda_sequence)
base_actuator.wait = False

mda_sequence2 = MDASequence(
    channels=[MY_CHANNELS[0]],
    time_plan={"interval": 1, "loops": 5},
)
base_actuator2 = MDAActuator(queue_manager, mda_sequence2)
base_actuator2.wait = False

base_actuator2.thread.start()
base_actuator.thread.start()

mmc.run_mda(queue_manager.acq_queue_iterator)
time.sleep(15)
queue_manager.stop_seq()
time.sleep(1)
