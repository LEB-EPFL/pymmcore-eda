from threading import Thread
from pymmcore_eda._logger import logger

class MockRunner():
    def __init__(self):
        self.events = []

    def run(self, events):
        self.thread = Thread(target=self._run, args=(events,))
        self.thread.start()

    def _run(self, events):
        _events = self.event_iterator(events)
        for event in _events:
            self.events.append(event)
            print(event.index['t'])
        logger.info('mock runner done')
    
    def event_iterator(self, events):
        yield from events