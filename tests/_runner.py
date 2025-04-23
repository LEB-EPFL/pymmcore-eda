import datetime
from threading import Thread
from pymmcore_eda._eda_event import EDAEvent
import time

class MockRunner:
    def __init__(self, time_machine=None, stop=object()) -> None:
        self.events = []
        self._axis_max: dict[str, int] = {}
        self.time_machine = time_machine
        self.stop = stop

    def run(self, events):
        self.thread = Thread(target=self._run, args=(events,))
        self.thread.start()

    def _run(self, events):
        _events = self.event_iterator(events)
        t0 = time.perf_counter()
        for event in _events:
            if event is None:
                continue
            elif event == self.stop:
                break
            if event.min_start_time is not None:
                time.sleep(max(event.min_start_time - (time.perf_counter() - t0), 0))

            if self.time_machine:
                acq_time = self.time_machine.event_seconds_elapsed()
                acq_time = datetime.timedelta(seconds=acq_time)
                acq_time = datetime.datetime.fromtimestamp(acq_time.total_seconds())

                acq_time = f"{acq_time.second:02d}.{acq_time.microsecond // 1000:03d}"
            else:
                acq_time = ""
            now = datetime.datetime.now()
            total_time = (
                f"{now.minute:02d}:{now.second:02d}.{now.microsecond//1000:03d}"
            )
            print(f"{total_time}|{acq_time} |{event}")
            self.events.append(event)

            for k, v in event.index.items():
                self._axis_max[k] = max(self._axis_max.get(k, 0), v)

    def event_iterator(self, events):
        yield from events
