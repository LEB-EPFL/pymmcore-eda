from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING

from useq import MDAEvent, Channel
import numpy as np

from src.pymmcore_eda._logger import logger
from smart_scan.custom_engine import CustomKeyes, GalvoParams
from smart_scan.helpers.function_helpers import ScanningStragies

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

        self.n_channels = mda_sequence.sizes.get("c", 1)
        self.channels = self.queue_manager.register_actuator(self, self.n_channels)

    def _run(self):
        # Adjust the channels to the ones supposed to be pushed to
        for event in self.mda_sequence:
            new_index = event.index.copy()
            new_index["c"] = self.channels[event.index.get("c", 0)]
            event = event.replace(index=new_index)
            if event.reset_event_timer and new_index.get('c', 0) > 0:
                event = event.replace(reset_event_timer=False)
            self.queue_manager.register_event(event)
        if self.wait:
            time.sleep(event.min_start_time + 3)

class SmartActuator_widefield:
    """Actuator that subscribes to new_interpretation and reacts to incoming events."""

    def __init__(self, queue_manager: QueueManager, hub: EventHub, n_channels : int, n_events: int = 3, skip_frames: bool = False):
        self.queue_manager = queue_manager
        self.hub = hub
        self.hub.new_interpretation.connect(self._act)
        self.n_events = n_events
        self.skip_frames= skip_frames
        self.n_channels = n_channels

    def _act(self, interpretation, event, metadata):
        
        print("\n")
        t_index = event.index.get("t", 0)
        logger.info(f'Generating {self.n_events} smart Widefield frames. t_index = {t_index}')
        print("\n")

        for i in range(1,self.n_events+1):

            curr_event = MDAEvent(channel={"config":"Cy5 (635nm)", "exposure": 100}, 
                            index={"t": -i, "c": self.n_channels}, 
                            min_start_time=0,
                            keep_shutter_open=True, # to hasten acquisition
                            )
            self.queue_manager.register_event(curr_event)
        
        # Empty the queue after the smart events are generated
        if self.skip_frames: self.queue_manager.empty_queue()


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

class MapStorage:
    def __init__(self):
        self.scan_map = np.zeros((2048, 2048))

    def save_map(self, map):
        self.scan_map = map

    def get_map(self):
        return self.scan_map

