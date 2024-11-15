from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from event_hub import EventHub
    import numpy as np
    from useq import MDAEvent
    from pymmcore_plus.metadata import FrameMetaV1


class Interpreter:
    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.new_analysis.connect(self.interpret)

    def interpret(self, img: np.ndarray, event: MDAEvent, metadata: FrameMetaV1):
        print(f"Interpreting data from event {event.index}")
        max_val = np.max(img)
        print(f"Max value in image: {max_val}")
        self.hub.new_interpretation.emit(max_val, event, metadata)
