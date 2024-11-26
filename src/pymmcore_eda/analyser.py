from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from tifffile import imread
from pathlib import Path

from pymmcore_eda._logger import logger

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent

class Analyser:
    """Analyse the image and produce an event score map for the interpreter."""

    def __init__(self, hub: EventHub):
        #self.new_image = np.zeros((64, 64)) #swap image from demo camera to something useful for testing
        self.hub = hub
        self.hub.frameReady.connect(self._analyse)

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        if event.index.get("c", 0) != 0:
            return
        logger.info("Analyser")
        img = imread(Path("C:/Users/kasia/Desktop/epfl/data/MAX_240930_calibration_002.ome.tif"))
        if event.index.get("t", 0) % 2 != 0:
            img = img / 10
        img[img < 5000] = 0
        logger.info(np.sum(img))
        self.hub.new_analysis.emit(img, event, metadata)
