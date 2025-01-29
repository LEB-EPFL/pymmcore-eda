from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from tifffile import imread, imwrite
from pathlib import Path
from tensorflow import keras
import tensorflow as tf
from threading import Thread
from pymmcore_plus.metadata.schema import FrameMetaV1

from smart_scan.helpers.function_helpers import normalize_tilewise_vectorized

from src.pymmcore_eda._logger import logger
from src.pymmcore_eda.writer import AdaptiveWriter
from useq import MDAEvent

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    

class AnalyserSettings:
    model_path: str = "/Volumes/LEB/Scientific_projects/deep_events_WS/data/original_data/training_data/20240224_0205_brightfield_cos7_n5_f1/20240224_0208_model.h5"

@tf.keras.utils.register_keras_serializable(package='deep_events', name='wmse_loss')
class WMSELoss(tf.keras.losses.Loss):
    def __init__(self, pos_weight=1, name='wmse_loss'):
        super().__init__(name=name)
        self.pos_weight = pos_weight

    def call(self, y_true, y_pred):
        weight_vector = y_true * self.pos_weight + (1. - y_true)
        return tf.reduce_mean(weight_vector * tf.square(y_true - y_pred))

    def get_config(self):
        return {'pos_weight': self.pos_weight}
tf.keras.utils.get_custom_objects().update({'WMSELoss': WMSELoss})

@tf.keras.utils.register_keras_serializable()
class WBCELoss(tf.keras.losses.Loss):
    def __init__(self, pos_weight=1, name='wbce_loss'):
        super().__init__(name=name)
        self.pos_weight = pos_weight
    def call(self, y_true, y_pred):
        bce = tf.keras.backend.binary_crossentropy(y_true, y_pred)
        # Apply the weights
        weight_vector = y_true * self.pos_weight + (1. - y_true)
        weighted_bce = weight_vector * bce
        return tf.keras.backend.mean(weighted_bce)

    def get_config(self):
        return {'pos_weight': self.pos_weight}    
tf.keras.utils.get_custom_objects().update({'WBCELoss': WBCELoss})

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

    output_save[0:256, 0:256] = 500

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
        settings = AnalyserSettings()
        self.hub = hub
        self.hub.frameReady.connect(self._analyse)
        self.model = keras.models.load_model(settings.model_path, compile = False)
        print("Model loaded")
        
        # Needed to write the network output on another channel
        # self.writer = writer
        
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
        
        # tile-wise normalisation of the image
        tile_size = 256
        try:
            self.img = normalize_tilewise_vectorized(arr=img, tile_size=tile_size)
        except AssertionError as e:
            self.img = img
            logger.info(f"Analyser: failed to perform tile-wise normalisation. {e}")
        
        self.event = event
        self.metadata = metadata
        if self.event.index.get("c", 0) != 0:
            return
        
        # logger.info('Fake data going in')
        # self.img = self.dummy_data[self.event.index.get("t", 0)]
        self.images[-1] = self.img

        def predict(images):
            if self.event.index.get("t", 0) < 4:
                return
            logger.info('PREDICTING')
            input = images.swapaxes(0,2)
            input = np.expand_dims(input, 0)
            input_cropped = input[:, 512:1536, 512:1536, :]
        
            output_cropped = self.model.predict(input_cropped)
            output_cropped = output_cropped[0, :, :, 0]
            
            output = np.zeros((2048, 2048))
            output[512:1536, 512:1536] = output_cropped
            print(f'Maximum value of the model output: {np.max(output)}\n')
            
            # Emits new_analysis signal
            self.hub.new_analysis.emit(output, event, metadata)
            
            # Emits new_writer_frame signal to store the network output
            emit_writer_signal(self.hub, event, output)

            logger.info("Analyser")


        predict_thread = Thread(target=predict, args=(self.images.copy(),))
        predict_thread.start()
        self.images[:-1] = self.images[1:]
