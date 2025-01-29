from __future__ import annotations

from typing import TYPE_CHECKING

from useq import MDAEvent
import numpy as np
from PIL import Image

from smart_scan.custom_engine import CustomKeyes, GalvoParams
from smart_scan.helpers.function_helpers import ScanningStragies

from src.pymmcore_eda.actuator import MapStorage

if TYPE_CHECKING:
    from event_hub import EventHub
    from queue_manager import QueueManager


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
            if True:
            # if map_diff > np.size(image) * 0.1:
               
                # Insert fake mask
                # mask = np.zeros((2048, 2048))
                # mask[1200:1600,600:1000] = 1
                # mask = Image.fromarray(mask.copy())
                # image[1024:1500, 1024:1500] = 0

                mask = Image.fromarray(image.copy())
                mask = mask.resize((124, 124))
                mask = np.array(mask, dtype=bool)
                h = mask.shape[0]
                ps = 102.4 / h # pixel size so that the total field of view is ~ 100 x 100 µm2
                print('DIFFERENT MAPS \n')
               
                for i in range(1,30):
                    event = MDAEvent(channel={"config":"DAPI (365nm)", "exposure": 100.}, 
                                    index={"t": -i, "c": 1}, 
                                    min_start_time=0,
                                    metadata={
                                        CustomKeyes.GALVO: {
                                            GalvoParams.SCAN_MASK: mask,
                                            GalvoParams.PIXEL_SIZE : ps,
                                            GalvoParams.STRATEGY: ScanningStragies.SNAKE,
                                            GalvoParams.DURATION : 0.1,
                                            GalvoParams.TRIGGERED : True,
                                            GalvoParams.TIMEOUT : 5
                                        }})
                    self.queue_manager.register_event(event)

                scan_map = image
            
            else:
                print('SAME MAPS\n')
            
            self.storage.save_map(scan_map)