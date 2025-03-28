from useq import Channel, MDAEvent, MDASequence

from pymmcore_eda._eda_event import EDAEvent


def test_from_mda_event_basic():
    """Test basic attribute copying from MDAEvent to EDAEvent."""
    # Create an MDAEvent with basic attributes
    mda_event = MDAEvent(
        min_start_time=10.5,
        exposure=100.0,
        x_pos=50.0,
        y_pos=60.0,
        z_pos=5.0,
        channel="DAPI",
    )

    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)

    # Check that attributes were properly copied
    assert eda_event.min_start_time == 10.5
    assert eda_event.exposure == 100.0
    assert eda_event.x_pos == 50.0
    assert eda_event.y_pos == 60.0
    assert eda_event.z_pos == 5.0
    assert eda_event.channel.config == "DAPI"


def test_from_mda_event_with_index():
    """Test that the index field is not copied."""
    # Create an MDAEvent with an index
    mda_event = MDAEvent(
        min_start_time=5.0,
        exposure=50.0,
        index={"time": 1, "position": 2, "channel": 0, "z": 3},
    )

    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)

    # Check that normal attributes were copied
    assert eda_event.min_start_time == 5.0
    assert eda_event.exposure == 50.0

    # Ensure index field was not copied
    assert eda_event.index is None
    # And that it didn't overwrite attach_index
    assert eda_event.attach_index is None


def test_from_mda_event_with_sequence():
    """Test handling of sequence attribute."""
    # Create an MDA sequence
    mda_sequence = MDASequence(
        channels=["DAPI", "GFP"], time_plan={"interval": 1.0, "loops": 3}
    )

    # Create an MDAEvent with a sequence
    mda_event = MDAEvent(min_start_time=0.0, sequence=mda_sequence)

    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)

    # Check that sequence was properly handled
    assert eda_event.sequence is not None
    # It should have copied the MDASequence, not converted it to EDASequence
    print(eda_event.sequence)
    assert isinstance(eda_event.sequence, MDASequence)
    assert eda_event.sequence.channels == (
        Channel(config="DAPI"),
        Channel(config="GFP"),
    )


def test_from_mda_event_with_metadata():
    """Test copying metadata dictionary."""
    # Create an MDAEvent with metadata
    mda_event = MDAEvent(
        min_start_time=0.0,
        metadata={
            "acquisition_name": "test_acq",
            "custom_field": 42,
            "nested": {"key": "value"},
        },
    )

    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)

    # Check that metadata was properly copied
    assert eda_event.metadata["acquisition_name"] == "test_acq"
    assert eda_event.metadata["custom_field"] == 42
    assert eda_event.metadata["nested"]["key"] == "value"


def test_from_mda_event_with_existing_attributes():
    """Test that from_mda_event overwrites existing attributes."""
    # Create an EDAEvent with existing attributes
    eda_event = EDAEvent(
        min_start_time=10.0, exposure=200.0, channel=Channel(config="GFP")
    )

    # Create an MDAEvent with different values
    mda_event = MDAEvent(min_start_time=5.0, exposure=100.0, channel="DAPI")

    # Use from_mda_event to update the existing EDAEvent
    eda_event.from_mda_event(mda_event)

    # Check that values were overwritten
    assert eda_event.min_start_time == 5.0
    assert eda_event.exposure == 100.0
    assert eda_event.channel.config == "DAPI"

import pytest
from useq import Channel, MDAEvent, MDASequence, PropertyTuple
from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._eda_sequence import EDASequence


def test_from_mda_event_basic():
    """Test basic attribute copying from MDAEvent to EDAEvent."""
    # Create an MDAEvent with basic attributes
    mda_event = MDAEvent(
        min_start_time=10.5,
        exposure=100.0,
        x_pos=50.0,
        y_pos=60.0,
        z_pos=5.0,
        channel="DAPI"
    )
    
    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)
    
    # Check that attributes were properly copied
    assert eda_event.min_start_time == 10.5
    assert eda_event.exposure == 100.0
    assert eda_event.x_pos == 50.0
    assert eda_event.y_pos == 60.0
    assert eda_event.z_pos == 5.0
    assert eda_event.channel.config == "DAPI"


def test_from_mda_event_with_index():
    """Test that the index field is not copied."""
    # Create an MDAEvent with an index
    mda_event = MDAEvent(
        min_start_time=5.0,
        exposure=50.0,
        index={
            "time": 1,
            "position": 2,
            "channel": 0,
            "z": 3
        }
    )
    
    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)
    
    # Check that normal attributes were copied
    assert eda_event.min_start_time == 5.0
    assert eda_event.exposure == 50.0
    
    # Ensure index field was not copied
    assert not hasattr(eda_event, "index")
    # And that it didn't overwrite attach_index
    assert eda_event.attach_index is None



def test_from_mda_event_with_sequence():
    """Test handling of sequence attribute."""
    # Create an MDA sequence
    mda_sequence = MDASequence(
        channels=["DAPI", "GFP"],
        time_plan={"interval": 1.0, "loops": 3}
    )
    
    # Create an MDAEvent with a sequence
    mda_event = MDAEvent(
        min_start_time=0.0,
        sequence=mda_sequence
    )
    
    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)
    
    # Check that sequence was properly handled
    assert eda_event.sequence is not None
    # It should have copied the MDASequence, not converted it to EDASequence
    print(eda_event.sequence)
    assert isinstance(eda_event.sequence, MDASequence)
    assert eda_event.sequence.channels == (Channel(config="DAPI"), Channel(config="GFP"))


def test_from_mda_event_with_metadata():
    """Test copying metadata dictionary."""
    # Create an MDAEvent with metadata
    mda_event = MDAEvent(
        min_start_time=0.0,
        metadata={
            "acquisition_name": "test_acq",
            "custom_field": 42,
            "nested": {"key": "value"}
        }
    )
    
    # Create an EDAEvent using from_mda_event
    eda_event = EDAEvent().from_mda_event(mda_event)
    
    # Check that metadata was properly copied
    assert eda_event.metadata["acquisition_name"] == "test_acq"
    assert eda_event.metadata["custom_field"] == 42
    assert eda_event.metadata["nested"]["key"] == "value"


def test_from_mda_event_with_existing_attributes():
    """Test that from_mda_event overwrites existing attributes."""
    # Create an EDAEvent with existing attributes
    eda_event = EDAEvent(
        min_start_time=10.0,
        exposure=200.0,
        channel=Channel(config="GFP")
    )
    
    # Create an MDAEvent with different values
    mda_event = MDAEvent(
        min_start_time=5.0,
        exposure=100.0,
        channel="DAPI"
    )
    
    # Use from_mda_event to update the existing EDAEvent
    eda_event.from_mda_event(mda_event)
    
    # Check that values were overwritten
    assert eda_event.min_start_time == 5.0
    assert eda_event.exposure == 100.0
    assert eda_event.channel.config == "DAPI"
