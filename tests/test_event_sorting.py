import queue

from useq import Channel

from pymmcore_eda._eda_event import EDAEvent  # Replace with actual import path
from pymmcore_eda._eda_sequence import EDASequence


class TestEDAEventSorting:
    """Test suite for EDAEvent comparison and sorting functionality."""

    def test_event_creation(self):
        """Test that events can be created with appropriate properties."""
        event = EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=0.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=EDASequence(axis_order="tpgcz"),
        )

        assert event.channel.config == "DAPI"
        assert event.z_pos == 0.0
        assert event.pos_index == 1
        assert event.min_start_time == 0.0
        print(event.sequence.axis_order)
        assert event.sequence.axis_order == ("t", "p", "g", "c", "z")

    def test_default_axis_order(self):
        """Test that events default to 'tpgcz' axis order."""
        event = EDAEvent(
            channel=Channel(config="DAPI"), z_pos=0.0, pos_index=1, min_start_time=0.0
        )

        assert event._get_axis_order() == ("t", "p", "g", "c", "z")

    def test_time_first_ordering(self):
        """Test sorting with 'tpgcz' axis order (time prioritized)."""
        sequence = EDASequence(axis_order="tpgcz")

        events = [
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=1.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="FITC"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=2,
                min_start_time=0.0,
                sequence=sequence,
            ),
        ]

        # Sort events (should prioritize time first)
        sorted_events = sorted(events)

        # First two events should have time=0, the last one time=1
        assert sorted_events[0].min_start_time == 0.0
        assert sorted_events[1].min_start_time == 0.0
        assert sorted_events[2].min_start_time == 1.0

        # For events with same time (0.0), check position ordering
        assert sorted_events[0].pos_index < sorted_events[1].pos_index

    def test_channel_first_ordering(self):
        """Test sorting with 'ctpgz' axis order (channel prioritized)."""
        sequence = EDASequence(
            axis_order="ctpgz",
            channels=[Channel(config="FITC"), Channel(config="DAPI")],
        )

        events = [
            EDAEvent(
                channel=Channel(config="FITC"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=1.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=2,
                min_start_time=0.0,
                sequence=sequence,
            ),
        ]

        # Sort events (should prioritize channel first)
        sorted_events = sorted(events)

        # Check that the channels are sorted accordingly, not alphabetically
        assert sorted_events[0].channel.config == "FITC"
        assert sorted_events[1].channel.config == "DAPI"
        assert sorted_events[2].channel.config == "DAPI"

        # For events with same channel (DAPI), check time ordering
        assert sorted_events[1].min_start_time < sorted_events[2].min_start_time

    def test_priority_queue(self):
        """Test that EDAEvents can be properly ordered in a PriorityQueue."""
        sequence = EDASequence(axis_order="tpgcz")

        # Create a priority queue
        event_queue = queue.PriorityQueue()

        # Add events in reverse order
        events = [
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=2.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=1.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=0.0,
                sequence=sequence,
            ),
        ]

        for event in events:
            event_queue.put(event)

        # Extract events from queue (should be in order by time)
        extracted_times = []
        while not event_queue.empty():
            extracted_times.append(event_queue.get().min_start_time)

        assert extracted_times == [0.0, 1.0, 2.0]

    def test_late_arriving_events(self):
        """Test that late-arriving events with earlier time get appropriate priority."""
        sequence = EDASequence(axis_order="tpgcz")

        # Create a priority queue
        event_queue = queue.PriorityQueue()

        # Add initial events
        events = [
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=5.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=3.0,
                sequence=sequence,
            ),
        ]

        for event in events:
            event_queue.put(event)

        # Later, add an event with earlier time
        late_event = EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=0.0,
            pos_index=1,
            min_start_time=1.0,
            sequence=sequence,
        )
        event_queue.put(late_event)

        # Extract events (earlier time should come first despite being added later)
        extracted_times = []
        while not event_queue.empty():
            extracted_times.append(event_queue.get().min_start_time)

        assert extracted_times == [1.0, 3.0, 5.0]

    def test_position_ordering(self):
        """Test that position indices are correctly ordered."""
        sequence = EDASequence(axis_order="ptgcz")  # Position first

        events = [
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=3,
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=2,
                min_start_time=0.0,
                sequence=sequence,
            ),
        ]

        # Sort events (should prioritize position first)
        sorted_events = sorted(events)

        # Check position ordering
        assert sorted_events[0].pos_index == 1
        assert sorted_events[1].pos_index == 2
        assert sorted_events[2].pos_index == 3

    def test_z_ordering(self):
        """Test that z positions are correctly ordered."""
        sequence = EDASequence(axis_order="ztpgc")  # Z first

        events = [
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=2.0,
                pos_index=1,
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=1.0,
                pos_index=1,
                min_start_time=0.0,
                sequence=sequence,
            ),
        ]

        # Sort events (should prioritize Z position first)
        sorted_events = sorted(events)

        # Check Z position ordering
        assert sorted_events[0].z_pos == 0.0
        assert sorted_events[1].z_pos == 1.0
        assert sorted_events[2].z_pos == 2.0

    def test_group_ordering(self):
        """Test that position groups (names) are correctly ordered."""
        sequence = EDASequence(axis_order="gtpcz")  # Group first

        events = [
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                pos_name="FieldC",
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                pos_name="FieldA",
                min_start_time=0.0,
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                pos_name="FieldB",
                min_start_time=0.0,
                sequence=sequence,
            ),
        ]

        # Sort events (should prioritize group/position name first)
        sorted_events = sorted(events)

        # Check position group ordering (alphabetical)
        assert sorted_events[0].pos_name == "FieldA"
        assert sorted_events[1].pos_name == "FieldB"
        assert sorted_events[2].pos_name == "FieldC"

    def test_none_values(self):
        """Test that None values are correctly handled (None is less than any value)."""
        sequence = EDASequence(axis_order="tpgcz")

        events = [
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=1.0,  # Not None
                sequence=sequence,
            ),
            EDAEvent(
                channel=Channel(config="DAPI"),
                z_pos=0.0,
                pos_index=1,
                min_start_time=None,  # None
                sequence=sequence,
            ),
        ]

        # Sort events (None should come before 1.0)
        sorted_events = sorted(events)

        assert sorted_events[0].min_start_time is None
        assert sorted_events[1].min_start_time == 1.0

    def test_get_priority_key(self):
        """Test the get_priority_key method for custom sorting."""
        event = EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=1.0,
            pos_index=2,
            pos_name="Field1",
            min_start_time=3.0,
            sequence=EDASequence(axis_order="tpgcz"),
        )

        # Default axis order from sequence (tpgcz)
        key1 = event.get_priority_key()
        assert key1[0] == 3.0  # t
        assert key1[1] == 2  # p
        assert key1[2] == "Field1"  # g
        assert key1[3] == "DAPI"  # c
        assert key1[4] == 1.0  # z

        # Override with custom axis order
        key2 = event.get_priority_key("czpgt")
        assert key2[0] == "DAPI"  # c
        assert key2[1] == 1.0  # z
        assert key2[2] == 2  # p
        assert key2[3] == "Field1"  # g
        assert key2[4] == 3.0  # t

    def test_equality(self):
        """Test that equality comparison works correctly."""
        sequence = EDASequence(axis_order="tpgcz")

        event1 = EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=0.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=sequence,
        )

        event2 = EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=0.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=sequence,
        )

        event3 = EDAEvent(
            channel=Channel(config="FITC"),  # Different channel
            z_pos=0.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=sequence,
        )

        # Same properties should be equal
        assert event1 == event2

        # Different channel should not be equal
        assert event1 != event3


def test_z_direction_ordering():
    """Test that z_direction parameter affects the z-ordering of events."""
    # Create a sequence with 'up' z_direction (default)
    up_sequence = EDASequence(axis_order="ztpgc", z_direction="up")

    # Create a sequence with 'down' z_direction
    down_sequence = EDASequence(axis_order="ztpgc", z_direction="down")

    # Create events with different z positions for 'up' sequence
    up_events = [
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=2.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=up_sequence,
        ),
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=0.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=up_sequence,
        ),
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=1.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=up_sequence,
        ),
    ]

    # Create similar events but for 'down' sequence
    down_events = [
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=2.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=down_sequence,
        ),
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=0.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=down_sequence,
        ),
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=1.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=down_sequence,
        ),
    ]

    # Sort up_events - with z_direction="up", lower z values should come first
    sorted_up_events = sorted(up_events)
    assert sorted_up_events[0].z_pos == 0.0
    assert sorted_up_events[1].z_pos == 1.0
    assert sorted_up_events[2].z_pos == 2.0

    # Sort down_events - with z_direction="down", higher z values should come first
    sorted_down_events = sorted(down_events)
    assert sorted_down_events[0].z_pos == 2.0
    assert sorted_down_events[1].z_pos == 1.0
    assert sorted_down_events[2].z_pos == 0.0

    # Test with events that have the same z values but different time values
    # to ensure z_direction only affects z comparisons
    mixed_up_events = [
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=1.0,
            pos_index=1,
            min_start_time=2.0,
            sequence=up_sequence,
        ),
        EDAEvent(
            channel=Channel(config="DAPI"),
            z_pos=1.0,
            pos_index=1,
            min_start_time=0.0,
            sequence=up_sequence,
        ),
    ]

    sorted_mixed_up = sorted(mixed_up_events)
    # Time should still be the primary sort factor for same z positions
    assert sorted_mixed_up[0].min_start_time == 0.0
    assert sorted_mixed_up[1].min_start_time == 2.0


def test_alternate_z_direction():
    """Test that alternate z_direction"""
    # Create a sequence with alternate z direction
    sequence = EDASequence(
        axis_order="czpgt", z_direction="alternate", channels=("DAPI", "FITC", "TRITC")
    )

    # Create events with different channels and z positions
    events = []

    # Create events for all channels and z positions
    for channel in ["DAPI", "FITC", "TRITC"]:
        for z in [0.0, 1.0, 2.0]:
            events.append(
                EDAEvent(
                    channel=Channel(config=channel),
                    z_pos=z,
                    pos_index=1,
                    min_start_time=0.0,
                    sequence=sequence,
                )
            )

    # Sort the events
    sorted_events = sorted(events)

    # With axis_order="czpgt", events should first be sorted by channel, then by z
    # For even channels (DAPI, TRITC), z should go up
    # For odd channels (FITC), z should go down
    expected_order = [
        ("DAPI", 0.0),
        ("DAPI", 1.0),
        ("DAPI", 2.0),  # DAPI (idx 0) goes up
        ("FITC", 2.0),
        ("FITC", 1.0),
        ("FITC", 0.0),  # FITC (idx 1) goes down
        ("TRITC", 0.0),
        ("TRITC", 1.0),
        ("TRITC", 2.0),  # TRITC (idx 2) goes up
    ]
    # Verify the sorted order
    for i, event in enumerate(sorted_events):
        expected_channel, expected_z = expected_order[i]
        assert (
            event.channel.config == expected_channel
        ), f"Expected channel {expected_channel}, got {event.channel.config} at {i}"
        assert (
            event.z_pos == expected_z
        ), f"Expected z_pos {expected_z}, got {event.z_pos} at index {i}"


if __name__ == "__main__":
    test_alternate_z_direction()
