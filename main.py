import time
from pathlib import Path
from pymmcore_plus import CMMCorePlus
from src.pymmcore_eda.actuator import MDAActuator, ButtonActuator, SmartActuator_widefield
from src.pymmcore_eda.analyser import Analyser, Dummy_Analyser
from src.pymmcore_eda.event_hub import EventHub
from src.pymmcore_eda.interpreter import Interpreter_widefield
from src.pymmcore_eda.queue_manager import QueueManager
from src.pymmcore_eda.writer import AdaptiveWriter
from src.pymmcore_eda.writer import AdaptiveWriter
from src.pymmcore_eda.event_hub import EventHub
from useq import Channel, MDASequence
from pathlib import Path


# User: Set the use case
use_microscope = False      
use_smart_scan = False      # If False, widefield is used
n_smart_events = 7         # Number of smart events generated after event detection
show_live_preview = True    # If True, the live preview is shown

# Dummy analysis toggle.
use_dummy_analysis = True   # If False, tensorflow is used to predict events

# Dummy Analysis parameters
prediction_time = 0.8

# Interpreter parameters
smart_event_period = (
    2  # smart event generation evert smart_event_period frames. 0 if not
)


# define the MDA sequence
mda_sequence = MDASequence(
    channels=(Channel(config="GFP (470nm)",exposure=10),),
    time_plan={"interval": 0.1, "loops": 50},
    keep_shutter_open_across = {'t', 'c'},
)

# Useful for debugging
skip_frames = False         # Empty the pymmcore-plus queue at the end of the series of generated smart events. Can help achieve a target frame-rate, at the expense of skipped frames
prediction_time = 0.8       # If use_dummy_analysis, prediction time in seconds
smart_event_period = 2      # Enforce a smart event generation evert smart_event_period frames. 0 if not enforcing

########################################

if __name__ == "__main__":
    
    # Set the log file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_log_file = Path(os.path.expanduser(f"~\\AppData\\Local\\pymmcore-plus\\pymmcore-plus\\logs\\pymmcore-plus_{timestamp}.log"))
    os.environ['PYMM_LOG_FILE'] = str(Path(__file__).parent /log_file_path)

    # Set the writer
    writer = AdaptiveWriter(path=Path(__file__).parent / saved_file_path, delete_existing=True)

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


# Instanciate the galvo scanners - dummy or real
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

    # Run the acquisition
    mmc.mda._reset_event_timer()
    queue_manager.time_machine._t0 = time.perf_counter()
    base_actuator.thread.start()
    mmc.run_mda(queue_manager.q_iterator, output=writer)
    base_actuator.thread.join()
    time.sleep(1)
    queue_manager.stop_seq()