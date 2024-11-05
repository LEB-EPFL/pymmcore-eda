from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
import useq 
from smart_scan.helpers.function_helpers import mask2active_pixels, ScanningStragies, pixels2voltages
from smart_scan.devices import Galvo_Scanners

class CustomEngine(MDAEngine):
    
    def setup_sequence(self, sequence: useq.MDASequence) -> SummaryMetaV1 | None:
        """Setup state of system (hardware, etc.) before an MDA is run.

        This method is called once at the beginning of a sequence.
        (The sequence object needn't be used here if not necessary)
        """
        
        # lasers off
        Galvo_Scanners.connect()
    
    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`.

        This method is called before each event in the sequence. It is
        responsible for preparing the state of the system for the event.
        The engine should be in a state where it can call `exec_event`
        without any additional preparation.
        """

        if 'scan_mask' in event.metadata:  
            self._smart_scan_setup(event.metadata)
        else:
            super().setup_event(event)

    def exec_event(self, event: useq.MDAEvent) -> object:
        """Execute `event`.

        This method is called after `setup_event` and is responsible for
        executing the event. The default assumption is to acquire an image,
        but more elaborate events will be possible.
        """
        return super().exec_event(event)
    
    def teardown_sequence(self, sequence: useq.MDASequence):
        # laser off
        Galvo_Scanners.disconnect()

    def _smart_scan_setup(self, metadata: dict) -> None:
        print(f"Setting up my custom device with {metadata}")
        scan_pixels = mask2active_pixels( mask=metadata["scan_mask"], scan_strategy=metadata["scanning_strategy"] )
        scan_voltages = pixels2voltages(scan_pixels)
        Galvo_Scanners.scan(scan_voltages[:,0],scan_voltages[:,1], metadata["rate"])


if __name__ == "__main__":
    core = CMMCorePlus.instance()
    core.loadSystemConfiguration()

    core.mda.set_engine(CustomEngine(core))

    experiment = [
        useq.MDAEvent(),
        useq.MDAEvent(metadata={'my_key': {'param1': 'val1'}}),  
        useq.MDAEvent(),
        useq.MDAEvent(metadata={'my_key': {'param1': 'val2'}}),
    ]

    core.run_mda(experiment)