from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING

from useq import MDAEvent, Channel

from pymmcore_eda._logger import logger

if TYPE_CHECKING:
    from event_hub import EventHub
    from queue_manager import QueueManager
    from useq import MDASequence


class MDAActuator:
    """Takes a MDASequence and sends events to the queue manager."""

    def __init__(self, queue_manager: QueueManager, mda_sequence: MDASequence):
        self.queue_manager = queue_manager
        self.mda_sequence = mda_sequence
        self.wait = True
        self.thread = Thread(target=self._run)

    def _run(self, wait=True):
        for event in self.mda_sequence:
            self.queue_manager.register_event(event)
        if self.wait:
            time.sleep(event.min_start_time + 3)


class ButtonActuator:
    """Actuator that sends events to the queue manager when a button is pressed."""

    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager
        self.thread = Thread(target=self._run)

    def _run(self):
        while True:
            button = input()
            if button == "q":
                break
            for i in range(1,4):
                event = MDAEvent(channel={"config":"mCherry (550nm)", "exposure": 10.}, index={"t": -i, "c": 2}, min_start_time=0)
                self.queue_manager.register_event(event)
            logger.info(f"Button {button} pressed, events sent to queue manager")


class SmartActuator:
    """Actuator that subscribes to new_interpretation and reacts to incoming events."""

    def __init__(self, queue_manager: QueueManager, hub: EventHub):
        self.queue_manager = queue_manager
        self.hub = hub
        self.hub.new_interpretation.connect(self._act)

    def _act(self, image, event, metadata):
        if event.index.get("t", 0) % 2 == 0:
            event = MDAEvent(index={"t": -1, "c": 2}, min_start_time=0)
            self.queue_manager.register_event(event)
            logger.info(f"SmartActuator sent {event}")
