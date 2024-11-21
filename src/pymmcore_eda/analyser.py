from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np

from pymmcore_eda._logger import logger

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent

class Analyser:
    """Analyse the image and produce an event score map for the interpreter."""

    def __init__(self, hub: EventHub):
        self.new_image = np.zeros((64, 64))
        self.hub = hub
        self.hub.frameReady.connect(self._analyse)

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        if event.index.get("c", 0) != 0:
            return
        logger.info("Analyser")
        img = self.new_image
        img[img < 5000] = 0
        self.hub.new_analysis.emit(img, event, metadata)
