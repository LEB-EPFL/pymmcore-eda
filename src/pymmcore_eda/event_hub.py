from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from psygnal import Signal, SignalGroup
from useq import MDAEvent

if TYPE_CHECKING:
    from pymmcore_plus.mda import MDARunner


class EventHub(SignalGroup):
    """Central hub for events in the pymmcore-eda system.

    Also receives signals form the pymmcore-plus Runner and relays
    them to the EDA components.
    """

    # pymmcore-plus events
    frameReady = Signal(np.ndarray, MDAEvent, dict)

    # internal events
    new_analysis = Signal(np.ndarray, MDAEvent, dict)
    new_interpretation = Signal(np.ndarray, MDAEvent, dict)

    def __init__(self, runner: MDARunner) -> None:
        self.runner = runner
        self.runner.events.frameReady.connect(self.frameReady.emit)
