import time

from pathlib import Path
import numpy as np
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

def test_frap_map_handling():
    """Test that the FRAP map handling in register_event performs logical OR on maps."""
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
    runner = MockRunner()
    runner.run(queue_manager.acq_queue_iterator)
    
    # Wait for queue manager warmup
    time.sleep(3)
    
    # Create two smaller FRAP maps (binary masks) for better visualization
    map1 = np.zeros((5, 5), dtype=bool)
    map1[1:3, 1:3] = True  # Set a small square region to True
    
    map2 = np.zeros((5, 5), dtype=bool)
    map2[2:4, 2:4] = True  # Set another overlapping square region to True
    
    # Print ASCII art of the maps for clarity
    print("\nMap 1:")
    print_bool_array(map1)
    
    print("\nMap 2:")
    print_bool_array(map2)
    
    # Expected result after logical OR
    expected_map = np.logical_or(map1, map2)
    print("\nExpected combined map (logical OR):")
    print_bool_array(expected_map)
    
    # Create an event with the first map
    event1 = EDAEvent(
        min_start_time=4.0, 
        channel='Cy5',
        metadata={'0': [map1, None]}  # Format matches the code's expectation
    )
    
    # Create an event with the second map
    event2 = EDAEvent(
        min_start_time=4.0,  # Same time to test map merging
        channel='Cy5',
        metadata={'0': [map2, None]}
    )
    
    # Register both events - the second should perform logical OR on the map
    queue_manager.register_event(event1)
    queue_manager.register_event(event2)
    
    # Wait for events to be processed
    time.sleep(7)
    queue_manager.stop_seq()
    
    # Find the event in the executed events
    cy5_events = [e for e in runner.events if e.channel.config == 'Cy5']
    
    # Assert that at least one event was executed
    assert len(cy5_events) > 0, "No Cy5 events were processed"
    
    # Get the metadata from the executed event
    event_map = None
    for event in cy5_events:
        if hasattr(event, 'metadata') and event.metadata and '0' in event.metadata:
            event_map = event.metadata['0'][0]
            break
    
    assert event_map is not None, "Could not find metadata map in processed events"
    
    print("\nActual result map:")
    print_bool_array(event_map)
    
    # Try to identify what's happening if they don't match
    if not np.array_equal(event_map, expected_map):
        print("\nMaps are not equal. Difference map (XOR):")
        diff_map = np.logical_xor(event_map, expected_map)
        print_bool_array(diff_map)
        
        # Check if it's doing a simple assignment instead of OR
        if np.array_equal(event_map, map2):
            print("It appears the second map is replacing the first map instead of OR'ing with it.")
        elif np.array_equal(event_map, map1):
            print("It appears the first map is being kept and the second map is being ignored.")
    
    # Verify the map has been logically OR'd
    np.testing.assert_array_equal(
        event_map, expected_map, 
        "FRAP map was not correctly combined with logical OR"
    )
    
    print("FRAP map handling test passed!")

def print_bool_array(arr):
    """Print a boolean array as ASCII art with X for True and . for False."""
    for row in arr:
        print(''.join('X' if cell else '.' for cell in row))

if __name__ == "__main__":
    test_frap_map_handling()
