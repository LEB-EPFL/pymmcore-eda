import time
from pathlib import Path

from pymmcore_plus import CMMCorePlus
from useq import Channel, MDASequence

from smart_scan.custom_engine import CustomEngine
from src.pymmcore_eda.actuator import (
    MDAActuator,
    SmartActuator_widefield,
)
from src.pymmcore_eda.analyser import Dummy_Analyser
from src.pymmcore_eda.event_hub import EventHub
from src.pymmcore_eda.interpreter import Interpreter_widefield
from src.pymmcore_eda.queue_manager import QueueManager
from src.pymmcore_eda.writer import AdaptiveWriter

mmc = CMMCorePlus()
mmc.setDeviceAdapterSearchPaths([*list(mmc.getDeviceAdapterSearchPaths())])
mmc.loadSystemConfiguration(
    "C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg"
)


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
mmc.setConfig("Channel", "Brightfield")

mmc.setProperty("pE-800", "Global State", 0)
# mmc.setProperty("pE-800", "SelectionA", 1)
# mmc.setProperty("pE-800", "IntensityA", 10)
# mmc.setProperty('Multi Shutter', 'Physical Shutter 1', 'ZeissReflectedLightShutter')
# mmc.setProperty('Multi Shutter', 'Physical Shutter 2', 'pE-800')
# mmc.setProperty('Core', 'Shutter', 'Multi Shutter')
mmc.setConfig("Channel", "DAPI (365nm)")

loc = Path(__file__).parent / "test_data/test.ome.zarr"
writer = AdaptiveWriter(path=loc, delete_existing=True)


hub = EventHub(mmc.mda, writer=writer)

queue_manager = QueueManager()

analyser = Dummy_Analyser(hub, smart_event_period=5, prediction_time=0)
# analyser = Analyser(hub)

# define the MDA sequence
mda_sequence = MDASequence(
    channels=(Channel(config="Brightfield", exposure=100),),
    time_plan={"interval": 1, "loops": 40},
    # keep_shutter_open=True, # to hasten acquisition
)
mmc.mda._reset_event_timer()  # noqa: SLF001
queue_manager.time_machine.reset_timer()

# initialise all the components
base_actuator = MDAActuator(queue_manager, mda_sequence)

# for smart widefield events
interpreter = Interpreter_widefield(hub)
smart_actuator = SmartActuator_widefield(queue_manager, hub, n_events=1)

# for smart scan events
# interpreter = Interpreter_scan(hub)
# smart_actuator = SmartActuator_scan(queue_manager, hub, n_events=5)

base_actuator.thread.start()
mmc.run_mda(queue_manager.q_iterator, output=writer)

base_actuator.thread.join()
time.sleep(1)
queue_manager.stop_seq()
