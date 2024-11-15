from psygnal import SignalGroup, Signal


class Hub(SignalGroup):
    new_event = Signal(str)

class Sender():
    new_event = Signal(str)
    def __init__(self, hub):
        self.hub = hub
        self.new_event.connect(self.hub.new_event)
    def run(self):
        self.new_event.emit(f"Event")

class Receiver():
    def __init__(self, hub):
        self.hub = hub
        self.hub.new_event.connect(self.on_new_event)

    def on_new_event(self, event):
        print(f"Received event: {event}")


class Sender2():
    def __init__(self, receiver):
        self.receivers = receivers
    def run(self):
        for receiver in self.receivers:
            receiver.on_new_event("Event")

class Receiver2():
    def on_new_event(self, event):
        print(f"Received event: {event}")


if __name__ == "__main__":
    hub = Hub()
    receiver = Receiver(hub)
    receiver2 = Receiver(hub)
    sender = Sender(hub)
    sender.run()