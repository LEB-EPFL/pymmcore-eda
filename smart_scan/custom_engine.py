from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
import useq
from smart_scan.helpers.function_helpers import ScanningStragies
from smart_scan.devices import Galvo_Scanners
from enum import IntEnum
import numpy as np
import threading
import time

from collections.abc import Sequence

class CustomKeyes(IntEnum):
    GALVO = 0


class GalvoParams(IntEnum):
    SCAN_MASK = 0
    PIXEL_SIZE = 1
    STRATEGY = 2
    DURATION = 3
    TRIGGERED = 4
    TIMEOUT = 5


class CustomEngine(MDAEngine):


    def __init__(self, mmc: CMMCorePlus, use_hardware_sequencing: bool = True) -> None:
        self._mmc = mmc
        self.use_hardware_sequencing = use_hardware_sequencing

        # used to check if the hardware autofocus is engaged when the sequence begins.
        # if it is, we will re-engage it after the autofocus action (if successful).
        self._af_was_engaged: bool = False
        # used to store the success of the last _execute_autofocus call
        self._af_succeeded: bool = False

        # used for one_shot autofocus to store the z correction for each position index.
        # map of {position_index: z_correction}
        self._z_correction: dict[int | None, float] = {}

        # This is used to determine whether we need to re-enable autoshutter after
        # the sequence is done (assuming a event.keep_shutter_open was requested)
        # Note: getAutoShutter() is True when no config is loaded at all
        self._autoshutter_was_set: bool = self._mmc.getAutoShutter()

        # -----
        # The following values are stored during setup_sequence simply to speed up
        # retrieval of metadata during each frame.
        # sequence of (device, property) of all properties used in any of the presets
        # in the channel group.
        self._config_device_props: dict[str, Sequence[tuple[str, str]]] = {}

        self._gs = Galvo_Scanners()

        print("In CustomEngine __init__")

    def setup_sequence(self, sequence: useq.MDASequence) -> None:
        """Setup state of system (hardware, etc.) before an MDA is run.

        This method is called once at the beginning of a sequence.
        (The sequence object needn't be used here if not necessary)
        """
        print('--> in setup_sequence')
        self._gs.connect()


    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`.

        This method is called before each event in the sequence. It is
        responsible for preparing the state of the system for the event.
        The engine should be in a state where it can call `exec_event`
        without any additional preparation.
        """
        print('--> in setup_event')
        
        if str(CustomKeyes.GALVO.value) in event.metadata:
            super().setup_event(event)
            self._smart_scan_setup(event.metadata)
        else:
            super().setup_event(event)

    def exec_event(self, event: useq.MDAEvent) -> object:
        """Execute `event`.

        This method is called after `setup_event` and is responsible for
        executing the event. The default assumption is to acquire an image,
        but more elaborate events will be possible.
        """
        print('--> in exec_event')
        return super().exec_event(event)

    def teardown_sequence(self, sequence: useq.MDASequence):
        print('--> in teardown_sequence')
        # self._gs.disconnect()


    def _smart_scan_setup(self, metadata: dict) -> None:
        print(f"--> Setting up the galvanometric mirrors")
        galvo_string = str(CustomKeyes.GALVO.value)

        # Define a wrapper function for the scan operation
        def scan_task():
            print("Starting scan task...")
            self._gs.scan(
                mask=metadata[galvo_string][GalvoParams.SCAN_MASK],
                pixelsize=metadata[galvo_string][GalvoParams.PIXEL_SIZE],
                scan_strategy=metadata[galvo_string][GalvoParams.STRATEGY],
                duration=metadata[galvo_string][GalvoParams.DURATION],
                triggered=metadata[galvo_string][GalvoParams.TRIGGERED],
                timeout=metadata[galvo_string][GalvoParams.TIMEOUT]
            )
            self._gs.disconnect()
            print("Ending scan task.")


        # Start the scan operation in a new thread
        scan_thread = threading.Thread(target=scan_task, daemon=False)
        scan_thread.start()
        
if __name__ == "__main__":
    core = CMMCorePlus.instance()
    core.setDeviceAdapterSearchPaths(
    ["C:/Program Files/Micro-Manager-2.0/", *list(core.getDeviceAdapterSearchPaths())]
    )
    core.loadSystemConfiguration()

    core.mda.set_engine(CustomEngine(core))
    # gs = Galvo_Scanners()

    # Disable hardware sequencing
    core.mda.engine.use_hardware_sequencing = False

    experiment = [
        useq.MDAEvent(),
        useq.MDAEvent(),
        useq.MDAEvent(
            metadata={
                CustomKeyes.GALVO: {
                    GalvoParams.SCAN_MASK: np.ones([40,40]),
                    GalvoParams.PIXEL_SIZE : 2.56,
                    GalvoParams.STRATEGY: ScanningStragies.SNAKE,
                    GalvoParams.DURATION : 1,
                    GalvoParams.TRIGGERED : False,
                    GalvoParams.TIMEOUT : 10
                    }
            }
        ),
        useq.MDAEvent(),
        useq.MDAEvent(
            metadata={
                CustomKeyes.GALVO: {
                    GalvoParams.SCAN_MASK: np.ones([40,40]),
                    GalvoParams.PIXEL_SIZE : 2.56,
                    GalvoParams.STRATEGY: ScanningStragies.RASTER,
                    GalvoParams.DURATION : 0.7,
                    GalvoParams.TRIGGERED : False,
                    GalvoParams.TIMEOUT : 10
                    }
            }
        ),
        ]

    core.run_mda(experiment)