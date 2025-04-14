import pytest
from useq import Channel, MDASequence
from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._event_queue import DynamicEventQueue

@pytest.fixture
def queue():
    """Create a fresh queue for each test."""
    return DynamicEventQueue()

@pytest.fixture
def sample_seq():
    return MDASequence(channels=["DAPI", "GFP", "TRITC", "Cy5"])

@pytest.fixture
def sample_events(sample_seq):
    """Create sample events with different dimensions."""
    event1 = EDAEvent(min_start_time=0.0, channel=Channel(config="DAPI"), z_pos=0.0)
    event2 = EDAEvent(min_start_time=5.0, channel=Channel(config="GFP"), z_pos=1.0)
    event3 = EDAEvent(min_start_time=10.0, channel=Channel(config="TRITC"), z_pos=2.0)
    event4 = EDAEvent(min_start_time=10.0, channel=Channel(config="Cy5"), z_pos=0.0)
    return event1, event2, event3, event4

def test_basic_queue_operations(queue, sample_events):
    """Test basic queue operations (add and get_next)."""
    event1, event2, event3, _ = sample_events
    
    # Add events in random order
    queue.add(event2)  # t=5.0
    queue.add(event3)  # t=10.0
    queue.add(event1)  # t=0.0
    
    # Check queue size
    assert len(queue) == 3
    
    # Check events come out in correct order
    assert queue.get_next().min_start_time == 0.0
    assert queue.get_next().min_start_time == 5.0
    assert queue.get_next().min_start_time == 10.0
    
    # Queue should be empty
    assert len(queue) == 0
    assert queue.get_next() is None

def test_dimension_indexing(queue, sample_events):
    """Test dimension indexing functionality."""
    event1, event2, event3, event4 = sample_events
    
    # Add events to populate unique value sets
    queue.add(event1)
    queue.add(event2)
    queue.add(event3)
    queue.add(event4)
    
    # Test time dimension values
    time_values = queue.get_unique_values('t')
    assert time_values == [0.0, 5.0, 10.0]
    
    # Test channel dimension values (order depends on SortedSet implementation)
    channel_values = set(queue.get_unique_values('c'))
    assert channel_values == {"DAPI", "GFP", "TRITC", "Cy5"}
    
    # Test z dimension values
    z_values = queue.get_unique_values('z')
    assert set(z_values) == {0.0, 1.0, 2.0}
    
    # Test getting values at specific indexes
    assert queue.get_value_at_index('t', 0) == 0.0
    assert queue.get_value_at_index('t', 1) == 5.0
    assert queue.get_value_at_index('t', 2) == 10.0
    
    # Test invalid index
    assert queue.get_value_at_index('t', 10) is None

def test_single_attach_index(queue, sample_events):
    """Test adding events with a single attach_index."""
    event1, event2, event3, _ = sample_events
    
    # Add events to populate unique values
    queue.add(event1)
    queue.add(event2)
    queue.add(event3)
    
    # Create new event with time index
    new_event = EDAEvent(attach_index = {'t': 1} )

    
    # Add the event
    queue.add(new_event)
    
    # Verify correct value was set
    assert new_event.min_start_time == 5.0
    
    # Verify event ordering
    times = []
    while len(queue) > 0:
        times.append(queue.get_next().min_start_time)
    
    assert times == [0.0, 5.0, 5.0, 10.0]

def test_multiple_attach_indices(queue, sample_events, sample_seq):
    """Test adding events with multiple attach_index dimensions."""
    event1, event2, event3, _ = sample_events
    
    # Add events to populate unique values
    queue.add(event1)
    queue.add(event2)
    queue.add(event3)
    
    # Create new event with multiple indices
    new_event = EDAEvent(attach_index = {
        't': 1,      # t=5.0
        'c': 0,      # c=DAPI
        'z': 2       # z=2.0
    })

    # Add the event
    queue.add(new_event)
    
    # Verify all dimensions were set correctly
    assert new_event.min_start_time == 5.0
    assert new_event.channel.config == "DAPI"
    assert new_event.z_pos == 2.0

def test_nonexistent_attach_index(queue, sample_events):
    """Test behavior with nonexistent attach indices."""
    event1 = sample_events[0]
    
    # Add events to populate unique values
    queue.add(event1)
    
    # Create event with invalid index
    new_event = EDAEvent()
    new_event.attach_index = {'t': 5}  # Index 5 doesn't exist
    
    # Add the event
    queue.add(new_event)
    
    # The time value should not be set since index doesn't exist
    assert new_event.min_start_time is None
    
    # But event should still be added to queue
    assert len(queue) == 2

def test_mixed_adding_schemes(queue, sample_events):
    """Test mixing direct value setting and attach_index."""
    event1, event2, _, _ = sample_events
    
    # Add events to populate unique values
    queue.add(event1)
    queue.add(event2)
    
    # Create event with both direct values and attach_index
    new_event = EDAEvent(z_pos=1.5)  # Set z directly
    new_event.attach_index = {'t': 1, 'c': 0}  # Set t and c via index
    
    # Add the event
    queue.add(new_event)
    
    # Verify correct combination of values
    assert new_event.min_start_time == 5.0  # From attach_index
    assert new_event.channel.config == "DAPI"  # From attach_index
    assert new_event.z_pos == 1.5  # From direct setting

def test_dynamic_indexing(queue, sample_events):
    """Test that indices update dynamically as values are added."""
    event1, event2, _, _ = sample_events
    
    # Start with empty queue
    assert len(queue.get_unique_values('t')) == 0
    
    # Add first event
    queue.add(event2)  # t=5.0
    assert queue.get_unique_values('t') == [5.0]
    
    # Add new event with earlier time
    queue.add(event1)  # t=0.0
    time_values = queue.get_unique_values('t')
    assert time_values == [0.0, 5.0]
    
    # Verify index 0 now points to t=0.0
    assert queue.get_value_at_index('t', 0) == 0.0
    
    # Add event with attach_index using updated indices
    new_event = EDAEvent()
    new_event.attach_index = {'t': 0}  # Should now be t=0.0
    queue.add(new_event)
    
    assert new_event.min_start_time == 0.0