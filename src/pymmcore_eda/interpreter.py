from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent
from pymmcore_eda._logger import logger


class Interpreter:
    """Get event score and produce a binary image that informs the actuator."""

    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.new_analysis.connect(self._interpret)

    def _interpret(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        logger.info("Interpreter")
        max_val = img > 1
        self.hub.new_interpretation.emit(max_val, event, metadata)
