from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from threading import Thread
from pymmcore_plus.metadata.schema import FrameMetaV1

from src.pymmcore_eda.helpers.function_helpers import normalize_tilewise_vectorized
from src.pymmcore_eda._logger import logger

from enum import IntEnum

from useq import MDAEvent

import time

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub

class CropLimits():
    def __init__(self, image_shape:tuple, crop_size:int):
        
        H, W = image_shape
        crop_size = min(crop_size, H, W)  # Restrict size if too large
        
        # Compute center coordinates
        center_y, center_x = H // 2, W // 2
        half_side = crop_size // 2

        # Define mask boundaries
        self.y_start, self.y_end = max(0, center_y - half_side), min(H, center_y + half_side)
        self.x_start, self.x_end = max(0, center_x - half_side), min(W, center_x + half_side)
        

class AnalyserSettings:
    
    n_frames_model: int = 4
    n_fake_predictions: int = 3      # number of initial fake predictions. The first ones are always longer
    tile_size: int = 256 # used for tile-wise normalisation.
    crop_size: int = 512 # crop the images before feeding the model. Used to haste inference. 
    image_shape: tuple = (2048,2048)
    
    # Calculated properties
    crop_limits = CropLimits(image_shape, crop_size)


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
    
    def __init__(self, hub: EventHub, prediction_time: float = 0.2):
        self.hub = hub
        self.hub.frameReady.connect(self._analyse)
        self.prediction_time = prediction_time
        self.predict_thread = None

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):

        if event.index.get("c", 0) != 0:
            return

        # Allows only one prediction thread at a time
        if self.predict_thread is None or not self.predict_thread.is_alive():
            
            # Perform the prediction in a separate thread
            predict_thread = Thread(target=dummy_predict, args=(img.copy(), event, metadata, self.hub, self.prediction_time))
            
            predict_thread.start()
            
            # Store the thread to avoid spawning multiple threads
            self.predict_thread = predict_thread

        
        
class Analyser:
    """Analyse the image and produce an event score map for the interpreter."""

    def __init__(self, hub: EventHub):
        # Import tensorflow here, so that we don't need to do it when
        # using DummyAnalyser
        from tensorflow import keras
        
        settings = AnalyserSettings()
        
        self.hub = hub
        self.model = keras.models.load_model(model_path, compile = False)
        self.n_frames_model = settings.n_frames_model
        self.predict_thread = None
        self.output = np.zeros(settings.image_shape)
        self.tile_size = settings.tile_size
        self.n_fake_predictions = settings.n_fake_predictions

        # Obtain the crop limits
        self.crop_limits = settings.crop_limits
        
        # connect the frameReady signal to the analyse method
        self.hub.frameReady.connect(self._analyse)
        
        self.images = np.zeros((self.n_frames_model+1, *settings.image_shape))

        # Perform a few first fake predictions - it takes a long time 
        img = self.images
        input = img.swapaxes(0,2)
        input = np.expand_dims(input, 0)
        input_cropped = input[:, self.crop_limits.y_start:self.crop_limits.y_end, self.crop_limits.x_start:self.crop_limits.x_end, :]
        for _ in range(self.n_fake_predictions):
            self.model.predict(input_cropped)

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict) -> None:
        # Skip if not the first channel
        if event.index.get("c", 0) != 0:
            return

        # tile-wise normalisation of the image
        try:
            img = normalize_tilewise_vectorized(arr=img, tile_size=self.tile_size)
        except AssertionError as e:
            img = np.divide(img, np.max(img))
            logger.info(f"Analyser: failed to perform tile-wise normalisation. {e}. Normalising the whole image instead.")
        
        # For test, use dummy data
        # self.img = self.dummy_data[self.event.index.get("t", 0)]
        
        # Add the current image to the list of images
        self.images[-1] = img

        # Allows only one prediction thread at a time
        if self.predict_thread is None or not self.predict_thread.is_alive():
            
            t_index = event.index.get("t", 0)
            
            # Perform the prediction in a separate thread
            predict_thread = Thread(target=predict, args=(self.images.copy(),t_index, event, self.model, self.hub, metadata, self.n_frames_model, self.output, self. crop_limits))
            
            # Store the thread to avoid spawning multiple threads
            self.predict_thread = predict_thread
            
            predict_thread.start()


        # Shift the images in the list
        self.images[:-1] = self.images[1:]

def dummy_predict(img,event, metadata, hub, prediction_time):
    # Determine the maximum possible value based on dtype
    dtype = img.dtype
    max_value = 1 
    if np.issubdtype(dtype, np.integer):
        max_value = np.iinfo(dtype).max
    elif np.issubdtype(dtype, np.floating):
        max_value = np.finfo(dtype).max

    # normalise the image
    output = img/max_value
    
    # Sleep for a while to simulate the prediction time
    t_start = time.time()
    time.sleep(prediction_time)
    elapsed = int((time.time() - t_start)*1000)
    t = event.index.get("t", 0) 
    logger.info(f"Dummy prediction finished for event t = {t}. Duration = {elapsed} ms. Max value: {np.max(output):.2f}")

    # Emit the event score
    hub.new_analysis.emit(output, event, metadata)

    # Emit new_writer_frame to store the network output
    emit_writer_signal(hub, event, output)


def predict(images,t_index, event, model, hub, metadata,n_frames_model, output, crop_limits):
    
    # Skip if the list of images is not full 
    if event.index.get("t", 0) < n_frames_model:
        return
    
    input = images.swapaxes(0,2)
    input = np.expand_dims(input, 0)
    input_cropped = input[:, crop_limits.y_start:crop_limits.y_end, crop_limits.x_start:crop_limits.x_end, :]

    # Perform and time the predection 
    t_start = time.time()
    output_cropped = model.predict(input_cropped)
    elapsed = int((time.time() - t_start)*1000)
    logger.info(f"Prediction finished for event t = {t_index}. Duration = {elapsed} ms. Max value: {np.max(output_cropped):.2f}")
    
    output_cropped = output_cropped[0, :, :, 0]
    output[crop_limits.y_start:crop_limits.y_end, crop_limits.x_start:crop_limits.x_end] = output_cropped
    
    # Emits new_analysis signal
    hub.new_analysis.emit(output, event, metadata)
    
    # Emits new_writer_frame signal to store the network output
    emit_writer_signal(hub, event, output)