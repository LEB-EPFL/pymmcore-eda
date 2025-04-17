from useq import MDAEvent, MDASequence

from pymmcore_eda._eda_sequence import EDASequence


def test_from_mda_event_with_sequence():
    """Test handling of sequence attribute."""
    # Create an MDA sequence
    mda_sequence = MDASequence(
        channels=["DAPI", "GFP"], time_plan={"interval": 1.0, "loops": 3}
    )
    print(mda_sequence.channels)
    eda_sequence = EDASequence().from_mda_sequence(mda_sequence)

    # Check sequence from an event
    mda_event = MDAEvent(min_start_time=0.0, sequence=mda_sequence)

    eda_sequence = EDASequence().from_mda_sequence(mda_event.sequence)

    assert eda_sequence.channels == mda_sequence.channels
