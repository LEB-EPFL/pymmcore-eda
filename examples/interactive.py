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

# Create and start an MDA actuator
base_actuator = MDAActuator(queue_manager, mda_sequence)
base_actuator.wait = False
base_actuator.thread.start()
time.sleep(1)


# Register various EDA events
event1 = EDAEvent(attach_index={"t": 2}, channel="DAPI")
queue_manager.register_event(event1)

event2 = EDAEvent(min_start_time=-4, channel="DAPI")
queue_manager.register_event(event2)

event3 = EDAEvent(attach_index={"t": 2}, channel="DAPI")
queue_manager.register_event(event3)

event4 = EDAEvent(min_start_time=-5.0, channel="Cy5")
event5 = EDAEvent(min_start_time=-5.1, channel="Cy5")
event6 = EDAEvent(min_start_time=-5.2, channel="Cy5")

for evt in (event4, event5, event6):
    queue_manager.register_event(evt)


button_actuator = ButtonActuator(queue_manager)
button_actuator.thread.start()
print("Starting acquisition sequence...")

# Start acquisition with hooks
try:
    # Start the base actuator
    mmc.mda._reset_event_timer()  # noqa: SLF001
    queue_manager.time_machine.reset_timer()
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
