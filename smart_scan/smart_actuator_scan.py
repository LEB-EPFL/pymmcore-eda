from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PIL import Image
from useq import MDAEvent

from smart_scan.custom_engine import CustomKeyes, GalvoParams
from smart_scan.helpers.function_helpers import ScanningStragies
from src.pymmcore_eda.actuator import MapStorage

if TYPE_CHECKING:
    from event_hub import EventHub
    from queue_manager import QueueManager


class SmartActuator_scan:
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
        self.storage = MapStorage()
        self.n_events = n_events
        self.skip_frames = skip_frames

    def _act(self, image, event, metadata):
        scan_map = self.storage.get_map()

        # check if we've already picked up this event
        # map_diff = np.sum(np.abs(np.int8(image) - np.int8(scan_map)))
        # if map_diff > np.size(image) * 0.1:

        if True:
            print(f"Generating {self.n_events} smart Scan frame\n")

            # Insert fake mask
            # mask = np.zeros((2048, 2048))
            # mask[1200:1600,600:1000] = 1
            # mask = Image.fromarray(mask.copy())
            # image[1024:1500, 1024:1500] = 0

            mask = Image.fromarray(image.copy())
            mask = mask.resize((124, 124))
            mask = np.array(mask, dtype=bool)
            h = mask.shape[0]
            ps = (
                102.4 / h
            )  # pixel size so that the total field of view is ~ 100 x 100 µm2

            for i in range(1, self.n_events + 1):
                event = MDAEvent(
                    channel={"config": "DAPI (365nm)", "exposure": 100.0},
                    index={"t": -i, "c": 1},
                    min_start_time=0,
                    keep_shutter_open=True,
                    metadata={
                        CustomKeyes.GALVO: {
                            GalvoParams.SCAN_MASK: mask,
                            GalvoParams.PIXEL_SIZE: ps,
                            GalvoParams.STRATEGY: ScanningStragies.SNAKE,
                            GalvoParams.DURATION: 0.1,
                            GalvoParams.TRIGGERED: True,
                            GalvoParams.TIMEOUT: 5,
                        }
                    },
                )
                self.queue_manager.register_event(event)

            scan_map = image

        else:
            print("SAME MAPS\n")

        self.storage.save_map(scan_map)

        # Empty the queue after the smart events are generated
        if self.skip_frames:
            self.queue_manager.empty_queue()
