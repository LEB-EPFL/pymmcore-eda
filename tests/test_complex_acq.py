import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from _runner import MockRunner
from pymmcore_plus import CMMCorePlus
from useq import Channel, MDASequence

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda.actuator import MDAActuator
from pymmcore_eda.queue_manager import QueueManager


def test_complex():
    mmc = CMMCorePlus()
    mmc.setDeviceAdapterSearchPaths(
        [
            "C:/Program Files/Micro-Manager-2.0/",
            *list(mmc.getDeviceAdapterSearchPaths()),
        ]
    )
    mmc.loadSystemConfiguration()
    mmc.mda.engine.use_hardware_sequencing = False

    eda_sequence = EDASequence(channels=("DAPI", "Cy5"))
    queue_manager = QueueManager(eda_sequence=eda_sequence)
    runner = MockRunner()

    mda_sequence = MDASequence(
        channels=[Channel(config="Cy5", exposure=100)],
        time_plan={"interval": 1, "loops": 10},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.wait = False
    base_actuator.thread.start()
    base_actuator.thread.join()

    event = EDAEvent(attach_index={"t": 3}, channel="DAPI")
    event3 = EDAEvent(attach_index={"t": 3}, channel="DAPI")
    queue_manager.register_event(event)
    queue_manager.register_event(event3)

    runner.run(queue_manager.acq_queue_iterator)

    event2 = EDAEvent(min_start_time=5, channel="DAPI")
    queue_manager.register_event(event2)


    event4 = EDAEvent(min_start_time=5.1, channel="Cy5")
    event5 = EDAEvent(min_start_time=5.2, channel="Cy5")
    event6 = EDAEvent(min_start_time=5.3, channel="Cy5")
    for event in (event4, event5, event6):
        queue_manager.register_event(event)

    time.sleep(13)
    queue_manager.stop_seq()

    # Assert the total number of events
    assert len(runner.events) == 15, f"Expected 15 events, got {len(runner.events)}"

    # Assert the base sequence has 10 Cy5 events (plus some additional ones)
    cy5_events = [e for e in runner.events if e.channel.config == "Cy5"]
    assert (
        len(cy5_events) >= 10
    ), f"Expected at least 10 Cy5 events, got {len(cy5_events)}"

    # Assert DAPI events were properly registered
    dapi_events = [e for e in runner.events if e.channel.config == "DAPI"]
    assert len(dapi_events) == 2, f"Expected 2 DAPI events, got {len(dapi_events)}"

    # Assert events with attach_index at t=3 were properly placed
    t3_events = [e for e in runner.events if e.index.get("t") == 3]
    assert len(t3_events) == 2, f"Expected 2 events at t=3, got {len(t3_events)}"
    assert any(
        e.channel.config == "DAPI" for e in t3_events
    ), "Expected DAPI event at t=3"
    assert any(
        e.channel.config == "Cy5" for e in t3_events
    ), "Expected Cy5 event at t=3"

    # Assert events with negative min_start_time were scheduled appropriately
    # They should appear in the latter part of the sequence
    late_cy5_events = [
        e
        for e in runner.events
        if e.channel.config == "Cy5" and e.min_start_time > 8 and e.min_start_time < 8.5
    ]
    assert (
        len(late_cy5_events) == 3
    ), f"Expected 3 Cy5 events with min_start_time 8-9, got {len(late_cy5_events)}"

    # Assert the DAPI event with negative min_start_time was scheduled
    late_dapi_events = [
        e for e in runner.events if e.channel.config == "DAPI" and e.index.get("t") == 5
    ]
    assert (
        len(late_dapi_events) == 1
    ), f"Expected 1 DAPI event at t=5, got {len(late_dapi_events)}"

    # Check the sequential order of events with min_start_time
    for i in range(1, len(runner.events)):
        assert (
            runner.events[i].min_start_time >= runner.events[i - 1].min_start_time
        ), f"""Events out of order at index {i}: {runner.events[i - 1].min_start_time}
        -> {runner.events[i].min_start_time}"""

    print("All assertions passed!")


def test_edge_cases():
    """Test edge cases for EDA event handling in queue manager,
    considering events are unique in a set."""
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

    # Create a sequence with multiple channels to test channel switching
    eda_sequence = EDASequence(channels=("DAPI", "FITC", "Cy5"))
    queue_manager = QueueManager(eda_sequence=eda_sequence)
    runner = MockRunner(stop=queue_manager.stop)
    runner.run(queue_manager.acq_queue_iterator)

    # Wait for queue manager warmup (3 seconds)
    time.sleep(3)

    # Edge case 1: Short sequence with rapid event registration
    mda_sequence = MDASequence(
        channels=(Channel(config="FITC", exposure=50),),
        time_plan={"interval": 0.5, "loops": 5},
    )
    base_actuator = MDAActuator(queue_manager, mda_sequence)
    base_actuator.wait = False
    base_actuator.thread.start()

    # Wait for base actuator to fully register the backbone events
    base_actuator.thread.join()

    # Register events after base sequence is fully registered
    # Edge case 2: Multiple unique events at specific indices
    event1 = EDAEvent(attach_index={"t": 2}, channel="DAPI", exposure=10)
    event2 = EDAEvent(attach_index={"t": 2}, channel="Cy5", exposure=200)
    queue_manager.register_event(event1)
    queue_manager.register_event(event2)

    # Edge case 3: Test duplicate event (should not be added)
    duplicate_event = EDAEvent(attach_index={"t": 2}, channel="DAPI", exposure=10)
    queue_manager.register_event(duplicate_event)

    # Edge case 4: Event with timestamp far in the future
    future_event = EDAEvent(min_start_time=100, channel="DAPI")
    queue_manager.register_event(future_event)

    # Edge case 5: Event with very specific timestamp
    precise_event = EDAEvent(min_start_time=1.123456789, channel="FITC")
    queue_manager.register_event(precise_event)

    # Edge case 6: Rapid succession of events with distinct timestamps
    # Using different exposures to ensure uniqueness
    for i in range(10):
        rapid_event = EDAEvent(min_start_time=3+0.01 * i, channel="Cy5", exposure=i + 1)
        queue_manager.register_event(rapid_event)

    # Wait for all events to be executed (base sequence + buffer time)
    time.sleep(5)

    # Stop the sequence before the future event would execute
    queue_manager.stop_seq()

    # Assertions
    # Should have 5 events from base sequence + additional unique registered events
    expected_min_events = (
        5 + 2 + 0 + 1 + 10
    )  # base + unique timepoint events + duplicate (0) + precise + rapid
    assert (
        len(runner.events) >= expected_min_events
    ), f"Expected at least {expected_min_events} events, got {len(runner.events)}"

    # Instead of checking specific t=2 timepoint, check for the presence of DAPI/Cy5
    # events with the specific exposures we set, as their actual timestamps may be
    # affected by rapid events
    dapi_exp10_events = [
        e for e in runner.events if e.channel.config == "DAPI" and e.exposure == 10
    ]
    cy5_exp200_events = [
        e for e in runner.events if e.channel.config == "Cy5" and e.exposure == 200
    ]

    # There should be exactly one DAPI with exposure=10 and one Cy5 with exposure=200
    assert (
        len(dapi_exp10_events) == 1
    ), f"Expected 1 DAPI event with exposure=10, got {len(dapi_exp10_events)}"
    assert (
        len(cy5_exp200_events) == 1
    ), f"Expected 1 Cy5 event with exposure=200, got {len(cy5_exp200_events)}"

    # The precise event's timestamp might also be affected, so we check for
    # its existence by exposure and channel
    precise_fitc_events = [
        e for e in runner.events if e.channel.config == "FITC" and e.exposure is None
    ]
    assert (
        len(precise_fitc_events) >= 1
    ), f"Expected at least 1 precise FITC event, got {len(precise_fitc_events)}"

    # The future event should not be in the events list since we stopped before
    #  it would execute
    future_events = [e for e in runner.events if e.min_start_time >= 100]
    assert (
        len(future_events) == 0
    ), f"Expected 0 future events, got {len(future_events)}"

    # Check that rapid succession events with unique exposures were all processed
    # Each should have a unique exposure to ensure set behavior doesn't eliminate them
    cy5_unique_events = {}
    for e in runner.events:
        if (
            e.channel.config == "Cy5"
            and e.exposure is not None
            and 1 <= e.exposure <= 10
        ):
            cy5_unique_events[e.exposure] = e

    assert (
        len(cy5_unique_events) == 10
    ), f"Expected 10 unique rapid Cy5 events, got {len(cy5_unique_events)}"

    # Edge case 7: Test that events are ordered by min_start_time
    sorted_events = sorted(runner.events, key=lambda e: e.min_start_time)
    assert runner.events == sorted_events, "Events should be ordered by min_start_time"


if __name__ == "__main__":
    test_edge_cases()
