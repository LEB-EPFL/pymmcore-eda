from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING

from useq import MDAEvent, Channel
import numpy as np
import cv2 as cv

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

    # def _act(self, image, event, metadata):
    #     if event.index.get("t", 0) % 2 == 0:
    #         event = MDAEvent(channel={"config":"mCherry (550nm)", "exposure": 10.}, index={"t": -1, "c": 2}, min_start_time=0)
    #         self.queue_manager.register_event(event)
    #         logger.info(f"SmartActuator sent {event}")

    def _act(self, image, event, metadata):
        if np.sum(image) != 0: #or something like np.sum(image) >= 20 (?)
            # prep binary map with squares
            contours, _ = cv.findContours(image.astype(np.uint8), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            centroids = []
            for contour in contours:
                # Calculate the moments for each contour
                M = cv.moments(contour)
                if M['m00'] != 0:  # To avoid division by zero
                    # Calculate the centroid coordinates
                    cX = int(M['m10'] / M['m00'])
                    cY = int(M['m01'] / M['m00'])
                    centroids.append((cX, cY))
            size=50 # size of the square
            for centroid in centroids:
                x, y = centroid
                image[y-size:y+size, x-size:x+size] = 1        
            # event = MDAEvent(channel={"config":"mCherry (550nm)", "exposure": 10.}, index={"t": -1, "c": 2}, min_start_time=0)
            # self.queue_manager.register_event(event)
            for i in range(1,4):
                event = MDAEvent(channel={"config":"mCherry (550nm)", "exposure": 10.}, 
                                 index={"t": -i, "c": 2}, 
                                 min_start_time=0,
                                 metadata={
                                     CustomKeyes.GALVO: {
                                         GalvoParams.SCAN_MASK: image,
                                         GalvoParams.STRATEGY: ScanningStragies.SNAKE,
                                         GalvoParams.RATE: 1 # this needs to come from exposure time
                                     }}) #added map in metadata
                self.queue_manager.register_event(event) #czy tu musi wysłać też image? Co z metadata? - ona tylko tam chilluje czy też ją ciągniemy?
            logger.info(f"SmartActuator sent {event}")
