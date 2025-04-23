from __future__ import annotations

import time
from queue import Queue
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, Mock, patch

import pytest
import useq
from useq import HardwareAutofocus, MDAEvent, MDASequence

from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.events import MDASignaler

from pymmcore_eda._runner import DynamicRunner


if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from pytest import LogCaptureFixture
    from pytestqt.qtbot import QtBot

    from pymmcore_plus.mda import MDAEngine

try:
    import pytestqt
except ImportError:
    pytestqt = None

SKIP_NO_PYTESTQT = pytest.mark.skipif(
    pytestqt is None, reason="pytest-qt not installed"
)


class BrokenEngine:
    def setup_sequence(self, sequence): ...

    def setup_event(self, event):
        raise ValueError("something broke")

    def exec_event(self, event): ...


@SKIP_NO_PYTESTQT
def test_mda_failures(core: CMMCorePlus, qtbot: QtBot) -> None:
    mda = MDASequence(
        channels=["Cy5"],
        time_plan={"interval": 1.5, "loops": 2},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
    )

    # error in user callback
    def cb(img, event):
        raise ValueError("uh oh")

    core.mda.events.frameReady.connect(cb)

    if isinstance(core.mda.events, MDASignaler):
        with qtbot.waitSignal(core.mda.events.sequenceFinished):
            core.mda.run(mda)

    assert not core.mda.is_running()
    assert not core.mda.is_paused()
    assert not core.mda._canceled
    core.mda.events.frameReady.disconnect(cb)

    # Hardware failure
    # e.g. a serial connection error
    # we should fail gracefully
    with patch.object(core.mda, "_engine", BrokenEngine()):
        if isinstance(core.mda.events, MDASignaler):
            with qtbot.waitSignal(core.mda.events.sequenceFinished):
                with pytest.raises(ValueError):
                    core.mda.run(mda)
        else:
            with qtbot.waitSignal(core.mda.events.sequenceFinished):
                with pytest.raises(ValueError):
                    core.mda.run(mda)
        assert not core.mda.is_running()
        assert not core.mda.is_paused()
        assert not core.mda._canceled


def event_generator() -> Iterator[MDAEvent]:
    yield MDAEvent()
    yield MDAEvent()
    return


SEQS = [
    MDASequence(time_plan={"interval": 1, "loops": 2}),
    (MDAEvent(), MDAEvent()),
    # the core fixture runs twice ... so we need to make this generator each time
    "event_generator()",
]


@SKIP_NO_PYTESTQT
@pytest.mark.parametrize("seq", SEQS)
def test_mda_iterable_of_events(
    core: CMMCorePlus, seq: Iterable[MDAEvent], qtbot: QtBot
) -> None:
    if seq == "event_generator()":  # type: ignore
        seq = event_generator()
    start_mock = Mock()
    frame_mock = Mock()

    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)    
    runner.events.sequenceStarted.connect(start_mock)
    runner.events.frameReady.connect(frame_mock)

    with qtbot.waitSignal(runner.events.sequenceFinished):
        runner.run(seq)

    # The signal emission from the Threads spun up by threading.Timer is not traced well.
    qtbot.wait(100)

    assert start_mock.call_count == 1
    assert frame_mock.call_count == 2


def test_keep_shutter_open(core: CMMCorePlus) -> None:
    # a 2-position sequence, where one position has a little time burst
    # and the other doesn't.  There is a z plan but we're only keeing shutter across
    # time.  The reason we use z is to do a little burst at each z, at one position
    # but not the other one (because only one position has time_plan)
    mda = MDASequence(
        axis_order="zpt",
        stage_positions=[
            (0, 0),
            useq.Position(
                sequence=MDASequence(
                    time_plan=useq.TIntervalLoops(interval=1, loops=3)
                )
            ),
        ],
        z_plan=useq.ZRangeAround(range=2, step=1),
        keep_shutter_open_across="t",
    )

    core.setAutoShutter(True)
    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)  
    
    @runner.events.frameReady.connect
    def _on_frame(img: Any, event: MDAEvent) -> None:
        assert core.getShutterOpen() == event.keep_shutter_open
        # autoshutter will always be on only at position 0 (no time plan)
        assert core.getAutoShutter() == (event.index["p"] == 0)

    runner.run(mda)
    

    # It should look like this:
    # event,                                                   open, auto_shut
    # index={'p': 0, 'z': 0},                                  False, True)
    # index={'p': 1, 'z': 0, 't': 0}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 0, 't': 1}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 0, 't': 2},                          False, False)
    # index={'p': 0, 'z': 1},                                  False, True)
    # index={'p': 1, 'z': 1, 't': 0}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 1, 't': 1}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 1, 't': 2},                          False, False)
    # index={'p': 0, 'z': 2},                                  False, True)
    # index={'p': 1, 'z': 2, 't': 0}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 2, 't': 1}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 2, 't': 2},                          False, False)
    # index={'p': 0, 'z': 3},                                  False, True)
    # index={'p': 1, 'z': 3, 't': 0}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 3, 't': 1}, keep_shutter_open=True), True, False)
    # index={'p': 1, 'z': 3, 't': 2},                          False, False)


def test_engine_protocol(core: CMMCorePlus) -> None:
    mock1 = Mock()
    mock2 = Mock()
    mock3 = Mock()
    mock4 = Mock()
    mock5 = Mock()
    mock6 = Mock()

    class MyEngine:
        def setup_sequence(self, mda: MDASequence) -> None:
            mock1(mda)

        def setup_event(self, event: MDAEvent) -> None:
            mock2(event)

        def exec_event(self, event: MDAEvent) -> None:
            mock3(event)

        def teardown_event(self, event: MDAEvent) -> None:
            mock4(event)

        def teardown_sequence(self, mda: MDASequence) -> None:
            mock5(mda)

        def event_iterator(self, events: Iterable[MDAEvent]) -> Iterator[MDAEvent]:
            mock6(events)
            return iter(events)
    runner = DynamicRunner()
    runner.set_engine(MyEngine())

    event = MDAEvent()
    runner.run([event])

    mock1.assert_called_once()
    mock2.assert_called_once_with(event)
    mock3.assert_called_once_with(event)
    mock4.assert_called_once_with(event)
    mock5.assert_called_once()
    mock6.assert_called_once_with([event])

    with pytest.raises(TypeError, match="does not conform"):
        runner.set_engine(object())  # type: ignore


@SKIP_NO_PYTESTQT
def test_runner_cancel(qtbot: QtBot) -> None:
    # not using the parametrized fixture because we only want to test Qt here.
    # see https://github.com/pymmcore-plus/pymmcore-plus/issues/95 and
    # https://github.com/pymmcore-plus/pymmcore-plus/pull/98
    # for what we're trying to avoid
    core = CMMCorePlus()
    core.loadSystemConfiguration('/opt/micro-manager/MMConfig_demo.cfg')
    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)  # type: ignore
    runner.engine.use_hardware_sequencing = False

    engine = MagicMock(wraps=runner.engine)
    runner.set_engine(engine)
    event1 = MDAEvent()

    from threading import Thread
    mda_th = Thread(target=runner.run, args=([event1, MDAEvent(min_start_time=10)],))
    mda_th.start()
    with qtbot.waitSignal(runner.events.sequenceCanceled):
        time.sleep(1)
        runner.cancel()
    qtbot.wait(100)

    engine.setup_sequence.assert_called_once()
    engine.setup_event.assert_called_once_with(event1)  # not twice


@SKIP_NO_PYTESTQT
def test_runner_pause(qtbot: QtBot) -> None:
    # not using the parametrized fixture because we only want to test Qt here.
    # see https://github.com/pymmcore-plus/pymmcore-plus/issues/95 and
    # https://github.com/pymmcore-plus/pymmcore-plus/pull/98
    # for what we're trying to avoid
    core = CMMCorePlus()
    core.loadSystemConfiguration('/opt/micro-manager/MMConfig_demo.cfg')
    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)  # type: ignore
    runner.engine.use_hardware_sequencing = False

    engine = MagicMock(wraps=runner.engine)
    runner.set_engine(engine)

    from threading import Thread
    with qtbot.waitSignal(runner.events.frameReady):
        mda_th = Thread(target=runner.run, args=([MDAEvent(), MDAEvent(min_start_time=2)],))
        mda_th.start()
    engine.setup_event.assert_called_once()  # not twice

    with qtbot.waitSignal(runner.events.sequencePauseToggled):
        runner.toggle_pause()
    time.sleep(1)
    with qtbot.waitSignal(runner.events.sequencePauseToggled):
        runner.toggle_pause()

    assert runner._paused_time > 0

    with qtbot.waitSignal(runner.events.sequenceFinished):
        mda_th.join()
    assert engine.setup_event.call_count == 2
    engine.teardown_sequence.assert_called_once()


def test_reset_event_timer(core: CMMCorePlus) -> None:
    seq = [
        MDAEvent(min_start_time=0, reset_event_timer=True),
        MDAEvent(min_start_time=0.2),
        MDAEvent(min_start_time=0, reset_event_timer=True),
        MDAEvent(min_start_time=0.2),
        MDAEvent(min_start_time=0.4),
    ]
    meta: list[float] = []
    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)  # type: ignore
    runner.events.frameReady.connect(lambda f, e, m: meta.append(time.perf_counter()*1000))
    runner.run(seq)

    # ensure that the 5th event occurred at least 190ms after the 4th event
    # The first after reset can be a little delayed
    # (allow some jitter)
    assert meta[4] >= meta[3] + 190


def test_queue_mda(core: CMMCorePlus) -> None:
    """Test running a Queue iterable"""
    mock_engine = MagicMock(wraps=core.mda.engine)
    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)  # type: ignore
    runner.set_engine(mock_engine)

    queue: Queue[MDAEvent | None] = Queue()
    queue.put(MDAEvent(index={"t": 0}))
    queue.put(MDAEvent(index={"t": 1}))
    queue.put(None)
    iterable_queue = iter(queue.get, None)

    runner.run(iterable_queue)
    # make sure that the engine's iterator was NOT used when running an iter(Queue)
    mock_engine.event_iterator.assert_not_called()
    assert mock_engine.setup_event.call_count == 2


def test_get_handlers(core: CMMCorePlus) -> None:
    """Test that we can get the handlers"""
    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)  # type: ignore

    assert not runner.get_output_handlers()
    on_start_names: list[str] = []
    on_finish_names: list[str] = []

    @runner.events.sequenceStarted.connect
    def _on_start() -> None:
        on_start_names.extend([type(h).__name__ for h in runner.get_output_handlers()])

    @runner.events.sequenceFinished.connect
    def _on_end() -> None:
        on_finish_names.extend([type(h).__name__ for h in runner.get_output_handlers()])

    runner.run([MDAEvent()], output="memory://")

    # weakref is used to store the handlers,
    # handlers should be cleared after the sequence is finished
    assert not runner.get_output_handlers()
    # but they should have been available during start and finish events
    assert on_start_names == ["TensorStoreHandler"]
    assert on_finish_names == ["TensorStoreHandler"]


def test_custom_action(core: CMMCorePlus) -> None:
    """Make sure we can handle custom actions gracefully"""
    runner = DynamicRunner()
    runner.set_engine(core.mda.engine)  # type: ignore
    runner.run([MDAEvent(action=useq.CustomAction())])

