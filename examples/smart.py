import time

from pymmcore_plus import CMMCorePlus
from useq import Channel, MDASequence

from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda.actuator import Actuator, MDAActuator
from pymmcore_eda.analyser import Analyser
from pymmcore_eda.event_hub import EventHub
from pymmcore_eda.interpreter import Interpreter
from pymmcore_eda.queue_manager import QueueManager

mmc = CMMCorePlus()
mmc.loadSystemConfiguration()
mmc.mda.engine.use_hardware_sequencing = False
print("Loaded system configuration")

event_hub = EventHub(mmc.mda)
eda_sequence = EDASequence(channels=("Cy5", "DAPI", "FITC"))
queue_manager = QueueManager(eda_sequence=eda_sequence)

# Create an MDA sequence with a Cy5 channel and time plan
mda_sequence = MDASequence(
    channels=(Channel(config="Cy5", exposure=100),),
    time_plan={"interval": 1, "loops": 30},
)


base_actuator = MDAActuator(queue_manager, mda_sequence)
base_actuator.wait = False
base_actuator.thread.start()
time.sleep(1)


analyser = Analyser(hub=event_hub, prediction_time=0.2)
interpreter = Interpreter(event_hub, smart_event_period=5)
smart_actuator = Actuator(queue_manager, event_hub)


mmc.mda._reset_event_timer()  # noqa: SLF001
queue_manager.time_machine.reset_timer()
mmc.run_mda(queue_manager.acq_queue_iterator)
time.sleep(35)
queue_manager.stop_seq()
