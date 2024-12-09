from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from matplotlib import pyplot as plt

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent
from pymmcore_eda._logger import logger

class InterpreterSettings:
    threshold: float = 0.999
    square_size: int = 50

class Interpreter:
    """Get event score and produce a binary image that informs the actuator."""

    def __init__(self, hub: EventHub):
        #self._storage(np.zeros((2048, 2048)))
        self.hub = hub
        self.hub.new_analysis.connect(self._interpret)

    def _interpret(self, net_out: np.ndarray, event: MDAEvent, metadata: dict):
        logger.info("Interpreter")
        mask = net_out > InterpreterSettings.threshold
        plt.imsave("C:/Users/kasia/Desktop/interpreter.png", mask) 
        coordinates = np.argwhere(mask)
        print(coordinates)
        for coord in coordinates:
            x, y = coord[0], coord[1]
            mask[x - InterpreterSettings.square_size : x + InterpreterSettings.square_size, y - InterpreterSettings.square_size : y + InterpreterSettings.square_size] = 1
        plt.imsave("C:/Users/kasia/Desktop/interpreter2.png", mask)
        print('INETRPRETER2 SAVED')
        self.hub.new_interpretation.emit(mask, event, metadata)
        print('INETRPRETER EMITTED')
    