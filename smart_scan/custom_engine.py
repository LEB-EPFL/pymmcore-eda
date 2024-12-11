from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
import useq
from smart_scan.helpers.function_helpers import ScanningStragies
from smart_scan.devices import Galvo_Scanners
from enum import IntEnum
import numpy as np
import threading


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

    def setup_sequence(self, sequence: useq.MDASequence) -> None:
        """Setup state of system (hardware, etc.) before an MDA is run.

        This method is called once at the beginning of a sequence.
        (The sequence object needn't be used here if not necessary)
        """
        # lasers off
        print('in setup_sequence \n')
        gs.connect()


    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`.

        This method is called before each event in the sequence. It is
        responsible for preparing the state of the system for the event.
        The engine should be in a state where it can call `exec_event`
        without any additional preparation.
        """
        print('in setup_event \n')
        
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
        print('in exec_event \n')
        return super().exec_event(event)

    def teardown_sequence(self, sequence: useq.MDASequence):
        # laser off
        print('in teardown_sequence \n')

    def _smart_scan_setup(self, metadata: dict) -> None:
        print(f"Setting up the galvanometric mirrors with {metadata}")
        
        galvo_string = str(CustomKeyes.GALVO.value)

        # Define a wrapper function for the scan operation
        def scan_task():
            print("Starting scan task...")
            gs.scan(
                mask=metadata[galvo_string][GalvoParams.SCAN_MASK],
                pixelsize=metadata[galvo_string][GalvoParams.PIXEL_SIZE],
                scan_strategy=metadata[galvo_string][GalvoParams.STRATEGY],
                duration=metadata[galvo_string][GalvoParams.DURATION],
                triggered=metadata[galvo_string][GalvoParams.TRIGGERED],
                timeout=metadata[galvo_string][GalvoParams.TIMEOUT]
            )
            print("Ending scan task.")
            gs.disconnect()

        # Start the scan operation in a new thread
        scan_thread = threading.Thread(target=scan_task, daemon=False)
        scan_thread.start()
        


if __name__ == "__main__":
    core = CMMCorePlus.instance()
    core.loadSystemConfiguration("smart_scan/resources/MMConfig_demo.cfg")

    core.mda.set_engine(CustomEngine(core))
    gs = Galvo_Scanners()


    from PIL import Image
    import time
    mask1 = np.array(Image.open('smart_scan/resources/mask_big_2.tif'))
    mask2 = np.array(Image.open('smart_scan/resources/Mask_square.tif'))
    

    experiment = [
        # useq.MDAEvent(),
        # useq.MDAEvent(),
        useq.MDAEvent(
            metadata={
                CustomKeyes.GALVO: {
                    GalvoParams.SCAN_MASK: np.ones([40,40]),
                    GalvoParams.PIXEL_SIZE : 2.56,
                    GalvoParams.STRATEGY: ScanningStragies.SNAKE,
                    GalvoParams.DURATION : 0.1,
                    GalvoParams.TRIGGERED : True,
                    GalvoParams.TIMEOUT : 10
                    }
            }
        ),
        useq.MDAEvent(),
        useq.MDAEvent(
            metadata={
                CustomKeyes.GALVO: {
                    GalvoParams.SCAN_MASK: np.ones([3,3]),
                    GalvoParams.PIXEL_SIZE : 0.1,
                    GalvoParams.STRATEGY: ScanningStragies.SNAKE,
                    GalvoParams.DURATION: 0.5,
                    GalvoParams.TRIGGERED : False,
                    GalvoParams.TIMEOUT : 2
                    }
            }
        ),
    ]

    core.run_mda(experiment)