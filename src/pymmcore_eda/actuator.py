from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._logger import logger

if TYPE_CHECKING:
    from typing import Any

    from useq import MDAEvent, MDASequence

    from pymmcore_eda.event_hub import EventHub
    from pymmcore_eda.queue_manager import QueueManager


class MDAActuator:
    """Takes a MDASequence and sends events to the queue manager."""

    def __init__(self, queue_manager: QueueManager, mda_sequence: MDASequence):
        self.queue_manager = queue_manager
        self.mda_sequence = mda_sequence
        self.wait = True
        self.thread = Thread(target=self._run)

        self.n_channels = mda_sequence.sizes.get("c", 1)
        self.settings = self.queue_manager.register_actuator(self, self.n_channels)

    def _run(self) -> None:
        for event in self.mda_sequence:
            self.queue_manager.register_event(event, self.settings.get("id", "0"))
        if self.wait:
            if event.min_start_time:
                time.sleep(event.min_start_time + 3)
            else:
                time.sleep(3)


class Actuator:
    """Actuator that subscribes to new_interpretation and reacts to incoming events."""

    def __init__(
        self,
        queue_manager: QueueManager,
        hub: EventHub,
        n_events: int = 3,
        skip_frames: bool = False,
    ):
        self.queue_manager = queue_manager
        self.hub = hub
        self.hub.new_interpretation.connect(self._act)
        self.n_events = n_events
        self.skip_frames = skip_frames

    def _act(self, _: Any, event: MDAEvent, __: Any) -> None:
        for i in range(0, self.n_events):
            curr_event = EDAEvent(
                channel="FITC",
                attach_index={"t": i},
            )
            self.queue_manager.register_event(curr_event)

        # Empty the queue after the smart events are generated
        if self.skip_frames:
            self.queue_manager.empty_queue()


class ButtonActuator:
    """Actuator that sends events to the queue manager when a button is pressed."""

    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager
        self.thread = Thread(target=self._run)

    def _run(self) -> None:
        while True:
            button = input()
            if button == "q":
                break
            event = EDAEvent(
                channel="FITC",
                attach_index={"t": 0},
            )
            self.queue_manager.register_event(event)
            logger.info(f"Button {button} pressed, {event} sent")
