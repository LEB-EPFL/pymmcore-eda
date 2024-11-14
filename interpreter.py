from event_hub import EventHub
import numpy as np
from useq import MDAEvent

class Interpreter:
    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.new_analysis.connect(self.interpret)

    def interpret(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        # Interpret the data
        print(f"Interpreting data from event {event.index}")
        max_val = np.max(img)
        print(f"Max value in image: {max_val}")
        self.hub.new_interpretation.emit(max_val, event, metadata)
