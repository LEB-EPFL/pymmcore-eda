from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from PIL import Image

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent
from src.pymmcore_eda._logger import logger

class InterpreterSettings:
    threshold: float = 0.8

class Interpreter_widefield:
    """Get event score and produce a binary image that informs the actuator."""

    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.new_analysis.connect(self._interpret)

    def _interpret(self, net_out: np.ndarray, event: MDAEvent, metadata: dict):
        mask = net_out > InterpreterSettings.threshold
        
        # Emit the interpretation result only if not empty
        if np.sum(mask) != 0:
            self.hub.new_interpretation.emit(mask, event, metadata)
    