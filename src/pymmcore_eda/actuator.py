from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING

from useq import MDAEvent, Channel
import numpy as np

from pymmcore_eda._logger import logger
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

    def _run(self, wait=True):
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

class SmartActuator:
    """Actuator that subscribes to new_interpretation and reacts to incoming events."""

    def __init__(self, queue_manager: QueueManager, hub: EventHub):
        self.queue_manager = queue_manager
        self.hub = hub
        self.hub.new_interpretation.connect(self._act)
        self.storage = MapStorage()

    def _act(self, image, event, metadata):
        scan_map = self.storage.get_map()
        if np.sum(image) != 0:
            # check if we've already picked up this event
            map_diff = np.sum(np.abs(np.int8(image) - np.int8(scan_map)))
            if map_diff > np.size(image) * 0.1:
                print('DIFFERENT MAPS')
                for i in range(1,4):
                    event = MDAEvent(channel={"config":"mCherry (550nm)", "exposure": 10.}, 
                                    index={"t": -i, "c": 2}, 
                                    min_start_time=0,
                                    metadata={
                                        CustomKeyes.GALVO: {
                                            GalvoParams.SCAN_MASK: image,
                                            #GalvoParams.PIXEL_SIZE : 0.1,
                                            GalvoParams.STRATEGY: ScanningStragies.SNAKE,
                                            #GalvoParams.DURATION : 1,
                                            #GalvoParams.TRIGGERED : True,
                                            #GalvoParams.TIMEOUT : 2
                                        }})
                    self.queue_manager.register_event(event)
                scan_map = image
            else:
                print('SAME MAPS')
            self.storage.save_map(scan_map)