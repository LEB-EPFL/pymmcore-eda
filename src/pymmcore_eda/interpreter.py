from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from event_hub import EventHub
    import numpy as np
    from useq import MDAEvent
    from pymmcore_plus.metadata import FrameMetaV1
from pymmcore_eda._logger import logger

class Interpreter:
    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.new_analysis.connect(self.interpret)

    def interpret(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        logger.info("Interpreter")
        max_val = img > 1
        self.hub.new_interpretation.emit(max_val, event, metadata)