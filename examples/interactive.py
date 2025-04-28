import time

from pymmcore_plus import CMMCorePlus
from useq import Channel, MDASequence

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda.actuator import ButtonActuator, MDAActuator
from pymmcore_eda.event_hub import EventHub
from pymmcore_eda.queue_manager import QueueManager

# Initialize CMMCorePlus
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
event_hub = EventHub(mmc.mda)
eda_sequence = EDASequence(channels=MY_CHANNELS)
queue_manager = QueueManager(eda_sequence=eda_sequence, mmcore=mmc)

# Create an MDA sequence with a Cy5 channel and time plan
mda_sequence = MDASequence(
    channels=(Channel(config=MY_CHANNELS[0], exposure=100),),
    time_plan={"interval": 1, "loops": 30},
)

# Create and start an MDA actuator
base_actuator = MDAActuator(queue_manager, mda_sequence)
base_actuator.wait = False
base_actuator.thread.start()
time.sleep(1)


# Register various EDA events
event1 = EDAEvent(attach_index={"t": 2}, channel=MY_CHANNELS[1])
queue_manager.register_event(event1)

event2 = EDAEvent(min_start_time=-4, channel=MY_CHANNELS[1])
queue_manager.register_event(event2)

event3 = EDAEvent(attach_index={"t": 2}, channel=MY_CHANNELS[1])
queue_manager.register_event(event3)

event4 = EDAEvent(min_start_time=-5.0, channel=MY_CHANNELS[0])
event5 = EDAEvent(min_start_time=-5.1, channel=MY_CHANNELS[0])
event6 = EDAEvent(min_start_time=-5.2, channel=MY_CHANNELS[0])

for evt in (event4, event5, event6):
    queue_manager.register_event(evt)


button_actuator = ButtonActuator(queue_manager)
button_actuator.channel_name = MY_CHANNELS[2]
button_actuator.thread.start()
print("Starting acquisition sequence...")

# Start acquisition with hooks
try:
    # Start the base actuator
    mmc.run_mda(queue_manager.acq_queue_iterator)

    # Wait for completion with timeout
    button_actuator.thread.join(timeout=60)

    # Stop the sequence
    print("Stopping sequence...")
    queue_manager.stop_seq()

    print("Acquisition finished")

except KeyboardInterrupt:
    print("Acquisition interrupted by user")
    queue_manager.stop_seq()

except Exception as e:
    print(f"Error during acquisition: {e}")
    queue_manager.stop_seq()

finally:
    # Ensure resources are released
    if hasattr(mmc, "reset"):
        mmc.reset()
    print("Clean up complete")
