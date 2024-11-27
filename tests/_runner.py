from threading import Thread


class MockRunner:
    def __init__(self):
        self.events = []
        self._axis_max: dict[str, int] = {}

    def run(self, events):
        self.thread = Thread(target=self._run, args=(events,))
        self.thread.start()

    def _run(self, events):
        _events = self.event_iterator(events)
        for event in _events:
            print(event)
            self.events.append(event)
            for k, v in event.index.items():
                self._axis_max[k] = max(self._axis_max.get(k, 0), v)

    def event_iterator(self, events):
        yield from events
