import time
from pathlib import Path

from pymmcore_plus import CMMCorePlus
from useq import Channel, MDASequence

from smart_scan.custom_engine import CustomEngine
from smart_scan.devices import DummyScanners, Galvo_Scanners
from smart_scan.interpreter_scan import Interpreter_scan
from smart_scan.smart_actuator_scan import SmartActuator_scan
from src.pymmcore_eda.actuator import (
    MDAActuator,
    SmartActuator_widefield,
)
from src.pymmcore_eda.analyser import Analyser, Dummy_Analyser
from src.pymmcore_eda.event_hub import EventHub
from src.pymmcore_eda.interpreter import Interpreter_widefield
from src.pymmcore_eda.queue_manager import QueueManager
from src.pymmcore_eda.writer import AdaptiveWriter

# Select the use case
use_dummy_galvo = True  # If True, dummy galvo scanners are used
use_microscope = True
use_smart_scan = False  # If False, widefield is used
n_smart_events = 10  # Number of smart events generated after event detection

# Empty the pymmcore-plus queue at the end of the series of generated smart events.
# Can help achieve a target frame-rate, at the expense of skipped frames
skip_frames = True

# Dummy analysis toggle.
use_dummy_analysis = True  # If False, tensorflow is used to predict events

# Dummy Analysis parameters
prediction_time = 0.3

# Interpreter parameters
smart_event_period = (
    2  # smart event generation evert smart_event_period frames. 0 if not
)


# define the MDA sequence
mda_sequence = MDASequence(
    channels=(Channel(config="GFP (470nm)", exposure=100),),
    time_plan={"interval": 1, "loops": 10},
    keep_shutter_open_across={"t", "c"},
)

########################################

mmc = CMMCorePlus()
mmc.setDeviceAdapterSearchPaths([*list(mmc.getDeviceAdapterSearchPaths())])

if use_microscope:
    try:
        mmc.loadSystemConfiguration(
            "C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg"
        )

        mmc.setProperty("Prime", "Trigger-Expose Out-Mux", 1)
        mmc.setProperty("Prime", "ExposeOutMode", "All Rows")

        mmc.setProperty("pE-800", "Global State", 0)
        mmc.setConfig("Channel", "Brightfield")
        mmc.setProperty("pE-800", "Global State", 0)
        mmc.setConfig("Channel", "DAPI (365nm)")
    except FileNotFoundError as e:
        print(f"Failed to load the Microscope System Configuration: \n{e}")
        raise

else:
    mmc.loadSystemConfiguration()

    mmc.setProperty("Camera", "OnCameraCCDXSize", 2048)
    mmc.setProperty("Camera", "OnCameraCCDYSize", 2048)

# Instantiate the galvo scanners - dummy or real
galvo_scanners = DummyScanners() if use_dummy_galvo else Galvo_Scanners()
mmc.mda.set_engine(CustomEngine(mmc, galvo_scanners))

mmc.mda.engine.use_hardware_sequencing = False
mmc.setChannelGroup("Channel")

# Set the writer
loc = Path(__file__).parent / "test_data/Test.ome.zarr"
writer = AdaptiveWriter(path=loc, delete_existing=True)

# initialise all components
hub = EventHub(mmc.mda, writer=writer)
queue_manager = QueueManager()
analyser = (
    Dummy_Analyser(hub, prediction_time=prediction_time)
    if use_dummy_analysis
    else Analyser(hub)
)
base_actuator = MDAActuator(queue_manager, mda_sequence)

if use_smart_scan:
    interpreter = Interpreter_scan(hub, smart_event_period=smart_event_period)
    smart_actuator = SmartActuator_scan(
        queue_manager, hub, n_events=n_smart_events, skip_frames=skip_frames
    )
else:
    interpreter = Interpreter_widefield(hub, smart_event_period=smart_event_period)
    smart_actuator = SmartActuator_widefield(
        queue_manager, hub, n_events=n_smart_events, skip_frames=skip_frames
    )

# Start and manage the acquisition
mmc.mda._reset_event_timer()  # noqa: SLF001
queue_manager.time_machine.reset_timer()

base_actuator.thread.start()
mmc.run_mda(queue_manager.q_iterator, output=writer)

base_actuator.thread.join()
time.sleep(1)
queue_manager.stop_seq()
