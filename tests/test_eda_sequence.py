import pytest
from useq import Channel

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda._event_queue import DynamicEventQueue


@pytest.fixture
def eda_sequence():
    """Create a sequence with a specific channel order."""
    # Define channel order: TRITC, DAPI, GFP, Cy5 (not alphabetical)
    seq = EDASequence(
        channels=["TRITC", "DAPI", "GFP", "Cy5"],
        axis_order=("c", "t", "z", "p", "g"),  # Channel first for this test
    )
    return seq


@pytest.fixture
def events_with_sequence(eda_sequence):
    """Create sample events with the sequence attached."""
    event1 = EDAEvent(
        min_start_time=0.0,
        channel=Channel(config="DAPI"),
        z_pos=0.0,
        sequence=eda_sequence,
    )
    event2 = EDAEvent(
        min_start_time=0.0,
        channel=Channel(config="GFP"),
        z_pos=0.0,
        sequence=eda_sequence,
    )
    event3 = EDAEvent(
        min_start_time=0.0,
        channel=Channel(config="TRITC"),
        z_pos=0.0,
        sequence=eda_sequence,
    )
    event4 = EDAEvent(
        min_start_time=0.0,
        channel=Channel(config="Cy5"),
        z_pos=0.0,
        sequence=eda_sequence,
    )
    return event1, event2, event3, event4


def test_channel_ordering_with_sequence(eda_sequence, events_with_sequence):
    """Test that events are ordered according to the channel order in the sequence."""
    event1, event2, event3, event4 = events_with_sequence

    # Create queue
    queue = DynamicEventQueue()

    # Add events in random order (not matching the sequence's channel order)
    queue.add(event2)  # GFP - should be 3rd
    queue.add(event4)  # Cy5 - should be 4th
    queue.add(event1)  # DAPI - should be 2nd
    queue.add(event3)  # TRITC - should be 1st

    # Get events in order and check channel order matches the sequence's channel order
    channels = []
    while len(queue) > 0:
        event = queue.get()
        channels.append(event.channel.config)

    # Expected order based on sequence.channels: TRITC, DAPI, GFP, Cy5
    assert channels == ["TRITC", "DAPI", "GFP", "Cy5"]


def test_mixed_sequence_and_no_sequence():
    """Test sorting events where some have a sequence and others don't."""
    # Create sequence with specific channel order
    seq = EDASequence(
        channels=["DAPI", "GFP", "TRITC", "Cy5"],
        axis_order=("t", "c", "z"),  # Channel first for this test
    )

    # Create events with sequence
    event1 = EDAEvent(min_start_time=0.0, channel=Channel(config="DAPI"), sequence=seq)
    event2 = EDAEvent(min_start_time=0.0, channel=Channel(config="GFP"), sequence=seq)

    # Create events without sequence
    event3 = EDAEvent(min_start_time=0.0, channel=Channel(config="TRITC"))
    event4 = EDAEvent(min_start_time=0.0, channel=Channel(config="Cy5"))

    # Create queue
    queue = DynamicEventQueue()

    # Add events in mixed order
    queue.add(event3)  # TRITC, no sequence
    queue.add(event1)  # DAPI, with sequence
    queue.add(event4)  # Cy5, no sequence
    queue.add(event2)  # GFP, with sequence

    # Get events and check order
    events = []
    while len(queue) > 0:
        events.append(queue.get())

    # Events with sequence should come first, in sequence channel order,
    # followed by events without sequence
    assert events[0].channel.config == "DAPI"  # First in sequence
    assert events[1].channel.config == "GFP"  # Second in sequence

    # Events without sequence should follow, but their exact order depends on
    # your implementation of _get_dimension_value for events without sequence
    assert events[2].sequence is None
    assert events[3].sequence is None

    # Make sure we have all events
    channel_configs = [e.channel.config for e in events]
    assert set(channel_configs) == {"DAPI", "GFP", "TRITC", "Cy5"}


def test_channel_not_in_sequence():
    """Test handling of channels that aren't defined in the sequence."""
    # Create sequence with specific channel order
    seq = EDASequence(
        channels=["DAPI", "GFP", "TRITC"],
        axis_order=("c", "t", "z"),  # Channel first for this test
    )

    # Create events with channels both in and not in the sequence
    event1 = EDAEvent(min_start_time=0.0, channel=Channel(config="DAPI"), sequence=seq)
    event2 = EDAEvent(min_start_time=0.0, channel=Channel(config="GFP"), sequence=seq)
    event3 = EDAEvent(min_start_time=0.0, channel=Channel(config="TRITC"), sequence=seq)
    event4 = EDAEvent(
        min_start_time=0.0, channel=Channel(config="Cy5"), sequence=seq
    )  # Not in sequence

    # Create queue
    queue = DynamicEventQueue()

    # Add events
    queue.add(event4)  # Cy5, not in sequence
    queue.add(event1)  # DAPI, in sequence
    queue.add(event3)  # TRITC, in sequence
    queue.add(event2)  # GFP, in sequence

    # Get events and check order
    events = []
    while len(queue) > 0:
        events.append(queue.get())

    # Events with channels in sequence should come first, in sequence order
    assert events[0].channel.config == "DAPI"
    assert events[1].channel.config == "GFP"
    assert events[2].channel.config == "TRITC"

    # Event with channel not in sequence should come last
    assert events[3].channel.config == "Cy5"


def test_attach_index_with_sequence():
    """Test attaching to indices with sequence channel data."""
    # Create sequence with specific channel order
    seq = EDASequence(
        channels=["DAPI", "GFP", "TRITC", "Cy5"], axis_order=("t", "c", "z")
    )

    # Create queue
    queue = DynamicEventQueue()

    # Add some initial events to populate the queue's unique values
    event1 = EDAEvent(min_start_time=0.0, channel=Channel(config="DAPI"), sequence=seq)
    event2 = EDAEvent(min_start_time=5.0, channel=Channel(config="GFP"), sequence=seq)
    queue.add(event1)
    queue.add(event2)

    # Create a new event with attach_index
    new_event = EDAEvent(
        attach_index={"t": 1, "c": 0},  # t=5.0, c=GFP
        sequence=seq,  # Important to set the sequence for proper channel indexing
    )
    queue.add(new_event)

    # Verify the event was properly configured
    assert new_event.min_start_time == 5.0
    assert new_event.channel.config == "DAPI"

    # Check sorting - all events should come out in order
    events = []
    while len(queue) > 0:
        events.append(queue.get())

    # Events should be sorted by time first, then channel (per seq.axis_order)
    print(events)
    assert len(events) == 3
    assert events[0].min_start_time == 0.0
    assert events[1].min_start_time == 5.0
    assert events[2].min_start_time == 5.0

    # For same time, should be sorted by channel
    # The events with t=5.0 should have GFP channel
    assert {events[1].channel.config, events[2].channel.config} == {"DAPI", "GFP"}
