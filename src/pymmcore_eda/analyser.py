from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from threading import Thread
from pymmcore_plus.metadata.schema import FrameMetaV1

from src.pymmcore_eda.helpers.function_helpers import normalize_tilewise_vectorized
from src.pymmcore_eda._logger import logger

from useq import MDAEvent

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    

class AnalyserSettings:
    # model_path: str = "//sb-nas1.rcp.epfl.ch/LEB/Scientific_projects/deep_events_WS/data/original_data/training_data/20240224_0205_brightfield_cos7_n5_f1/20240224_0208_model.h5"
    model_path: str = "/Volumes/LEB/Scientific_projects/deep_events_WS/data/original_data/training_data/20240224_0205_brightfield_cos7_n5_f1/20240224_0208_model.h5"
    n_frames_model = 4


def emit_writer_signal(hub, event: MDAEvent, output, custom_channel : int = 2):
    """
    Emit the new_writer_frame signal.

    Parameters:
    hub (EventHub): The event hub to emit the signal.
    event (MDAEvent): The event containing t_index and metadata about the frame.
    output (np.ndarray): The output data to be emitted.
    custom_channel (int, optional): The custom channel index. Defaults to 2.
    """
    t_index = event.index.get("t", 0)
    
    fake_event = MDAEvent(channel=event.channel, index={"t": t_index, "c": custom_channel}, min_start_time=0)
    
    output_save = np.array(output*1e4)

    # output_save[0:256, 0:256] = 500

    output_save = np.transpose(output_save)
    output_save = output_save.astype('uint16')
    meta = FrameMetaV1(fake_event)

    hub.new_writer_frame.emit(output_save, fake_event, meta)


class Dummy_Analyser:
    """Analyse the image and produce a map for the interpreter."""
    
    def __init__(self, hub: EventHub):
        self.hub = hub
        self.hub.frameReady.connect(self._analyse)

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):

        if event.index.get("c", 0) != 0:
            return

        # Determine the maximum possible value based on dtype
        dtype = img.dtype
        max_value = 1 
        if np.issubdtype(dtype, np.integer):
            max_value = np.iinfo(dtype).max
        elif np.issubdtype(dtype, np.floating):
            max_value = np.finfo(dtype).max

        img[200,200] = 65520

        # normalise and filter the image
        img_norm = img/max_value
        
        threshold = 0.1
        img_norm[img_norm <= threshold] = 0
        
        output = img_norm
        print(f'Event score max: {np.max(output)}')
        print(f'Event score min: {np.min(output)}')

        # Emit the event score
        self.hub.new_analysis.emit(output, event, metadata)

        # Emit new_writer_frame to store the network output
        emit_writer_signal(self.hub, event, output)

        logger.info("Dummy Analyser")

class Analyser:
    """Analyse the image and produce an event score map for the interpreter."""

    def __init__(self, hub: EventHub):
        
        # Import tensorflow here, so that we don't need to do it when using DummyAnalyser
        from tensorflow import keras
        
        settings = AnalyserSettings()
        
        self.hub = hub
        self.model = keras.models.load_model(settings.model_path, compile = False)
        self.n_frames_model = settings.n_frames_model
        self.output = np.zeros((2048, 2048))
        
        # connect the frameReady signal to the analyse method
        self.hub.frameReady.connect(self._analyse)
        
        self.images = np.zeros((5, 2048, 2048))
        # self.dummy_data = imread(Path("C:/Users/glinka/Desktop/stk_0010_FOV_1_MMStack_Default.ome.tif"))
        # img = self.dummy_data[0:3]

        # Perform a few first fake predictions - take a long time 
        img = self.images
        input = img.swapaxes(0,2)
        input = np.expand_dims(input, 0)

        # Crop all the images to haste prediction
        input_cropped = input[:, 512:1536, 512:1536, :]
        self.model.predict(input_cropped)
        self.model.predict(input_cropped)
        self.model.predict(input_cropped)
        self.model.predict(input_cropped)

    
    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        
        # Skip if not the first channel
        if event.index.get("c", 0) != 0:
            return

        # tile-wise normalisation of the image
        tile_size = 256
        try:
            img = normalize_tilewise_vectorized(arr=img, tile_size=tile_size)
        except AssertionError as e:
            img = img
            logger.info(f"Analyser: failed to perform tile-wise normalisation. {e}")
        
        # self.event = event
        # self.metadata = metadata
        # logger.info('Fake data going in')
        # self.img = self.dummy_data[self.event.index.get("t", 0)]
        
        # Add the current image to the list of images
        self.images[-1] = img

        t_index = event.index.get("t", 0)
        predict_thread = Thread(target=predict, args=(self.images.copy(),t_index, event, self.model, self.hub, metadata, self.n_frames_model, self.output))
        predict_thread.start()
        
        # Shift the images in the list
        self.images[:-1] = self.images[1:]


def predict(images,t_index, event, model, hub, metadata,n_frames_model, output):
    
    # Skip if the list of images is not full 
    if event.index.get("t", 0) < n_frames_model:
        return
    
    input = images.swapaxes(0,2)
    input = np.expand_dims(input, 0)
    input_cropped = input[:, 512:1536, 512:1536, :]

    # logger.info('Prediction Started')
    output_cropped = model.predict(input_cropped)
    logger.info(f"Prediction finished for event t = {t_index}. Max value: {np.max(output_cropped):.2f}")
    output_cropped = output_cropped[0, :, :, 0]
    output[512:1536, 512:1536] = output_cropped
    
    # Emits new_analysis signal
    hub.new_analysis.emit(output, event, metadata)
    
    # Emits new_writer_frame signal to store the network output
    emit_writer_signal(hub, event, output)