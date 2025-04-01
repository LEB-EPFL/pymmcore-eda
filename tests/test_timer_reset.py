import time

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from pymmcore_plus import CMMCorePlus
from useq import MDASequence
from pymmcore_eda.actuator import MDAActuator
from pymmcore_eda.queue_manager import QueueManager
from useq import Channel
from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda._eda_event import EDAEvent
from _runner import MockRunner

def test_reset_event_timer():
    """Test that the reset_event_timer on EDAEvent properly resets the timer."""
    # Setup the core components
    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False
    
    # Create a sequence with multiple channels
    eda_sequence = EDASequence(channels=("DAPI", "Cy5"))
    queue_manager = QueueManager(eda_sequence=eda_sequence)
    runner = MockRunner(time_machine=queue_manager.time_machine)
    runner.run(queue_manager.acq_queue_iterator)
    
    # Wait for queue manager warmup
    time.sleep(3)
    
    # Create and start a base sequence
    mda_sequence = MDASequence(
        channels=(Channel(config="Cy5", exposure=100),),
        time_plan={"interval": 1, "loops": 5},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.wait = False
    base_actuator.thread.start()
    base_actuator.thread.join()
    
    # Create an event with reset_event_timer=True
    # This should reset the timer when it's processed
    reset_event = EDAEvent(min_start_time=1.0, channel='DAPI', reset_event_timer=True)
    queue_manager.register_event(reset_event)
    
    # Create events that should be affected by the timer reset
    event1 = EDAEvent(min_start_time=2.0, channel='Cy5')
    event2 = EDAEvent(min_start_time=3.0, channel='Cy5')
    event2 = EDAEvent(min_start_time=4.0, channel='Cy5')
    queue_manager.register_event(event1)
    queue_manager.register_event(event2)
    
    # Wait for all events to be processed
    time.sleep(7)
    queue_manager.stop_seq()
    
    # Get the events that were processed after the reset_event
    reset_event_idx = None
    for i, event in enumerate(runner.events):
        if event.channel.config == 'DAPI' and hasattr(event, 'reset_event_timer') and event.reset_event_timer:
            reset_event_idx = i
            break
    
    assert reset_event_idx is not None, "Reset event was not processed"
    
    # The events after the reset should have their timing adjusted 
    # Check that the timing between events is as expected
    if len(runner.events) > reset_event_idx + 2:
        # Get the events after the reset
        post_reset_events = runner.events[reset_event_idx+1:]
        
        # Check that the first event after reset was processed soon after the reset event
        # (not waiting for the full original min_start_time)
        reset_time = runner.events[reset_event_idx].min_start_time
        next_event_time = post_reset_events[1].min_start_time
        
        # The time difference should be close to the interval between events (around 1 second)
        # rather than the original absolute time (which would be 2.0)
        time_diff = next_event_time - reset_time
        assert 0.9 <= time_diff <= 1.1, f"Expected time difference around 1.0, got {time_diff}"
        
        # Check the spacing between subsequent events
        if len(post_reset_events) >= 2:
            print(post_reset_events[1])
            second_event_time = post_reset_events[3].min_start_time
            print(second_event_time)
            second_time_diff = second_event_time - next_event_time
            assert 0.9 <= second_time_diff <= 1.1, f"Expected time difference around 1.0, got {second_time_diff}"
    
    print("Reset event timer flag test passed!")

if __name__ == "__main__":
    test_reset_event_timer()