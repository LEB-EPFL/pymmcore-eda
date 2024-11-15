from event_hub import EventHub
import numpy as np
from useq import MDAEvent
from psygnal import Signal

class Analyser:
    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.frameReady.connect(self.analyse)

    def analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        if event.index.get('c', 0) != 0:
            return
        # Analyse the data
        print(f"Analysing data from event {event.index}")
        img[img < 5000] = 0
        self.hub.new_analysis.emit(img, event, metadata)
