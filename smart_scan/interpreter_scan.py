from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent
from src.pymmcore_eda._logger import logger

class InterpreterSettings:
    threshold: float = 0.9
    square_semi_size: int = 60 #px

class Interpreter_scan:
    """Get event score and produce a binary image that informs the actuator."""

    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.new_analysis.connect(self._interpret)

    def _interpret(self, net_out: np.ndarray, event: MDAEvent, metadata: dict):
        logger.info("Interpreter for smart scan")
        mask = net_out > InterpreterSettings.threshold
        coordinates = np.argwhere(mask)
        
        for coord in coordinates:
            x, y = coord[0], coord[1]
            mask[x - InterpreterSettings.square_semi_size : x + InterpreterSettings.square_semi_size, y - InterpreterSettings.square_semi_size : y + InterpreterSettings.square_semi_size] = 1
        
        # Emit the interpretation result only if not empty
        if np.sum(mask) != 0:
            self.hub.new_interpretation.emit(mask, event, metadata)