from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from tifffile import imread, imwrite
from pathlib import Path
from tensorflow import keras
import tensorflow as tf
from threading import Thread

from PIL import Image

from src.pymmcore_eda._logger import logger

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent

class AnalyserSettings:
    model_path: str = "//sb-nas1.rcp.epfl.ch/leb/Scientific_projects/deep_events_WS/data/original_data/training_data/20240224_0205_brightfield_cos7_n5_f1/20240224_0208_model.h5"

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

class Analyser:
    """Analyse the image and produce an event score map for the interpreter."""

    def __init__(self, hub: EventHub):
        settings = AnalyserSettings()
        self.hub = hub
        self.hub.frameReady.connect(self._analyse)
        self.model = keras.models.load_model(settings.model_path)
        print("Model loaded")
        self.images = np.zeros((5, 2048, 2048))

        # Perform a first fake prediction - takes a long time 
        # self.dummy_data = imread(Path("C:/Users/glinka/Desktop/stk_0010_FOV_1_MMStack_Default.ome.tif"))
        # img = self.dummy_data[0:3]
        
        img = self.images
        input = img.swapaxes(0,2)
        input = np.expand_dims(input, 0)
        self.model.predict(input)


    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        
        print(f"Max value: {np.max(img)}")

        img = img - np.min(img)
        self.img = np.divide(img,np.max(img))

        self.event = event
        self.metadata = metadata
        if self.event.index.get("c", 0) != 0:
            return
        
        # logger.info('Fake data going in')
        # self.img = self.dummy_data[self.event.index.get("t", 0)]

        self.images[-1] = self.img
        
        def predict():
            if self.event.index.get("t", 0) < 4:
                return
            else:
                logger.info('PREDICTING')
                input = self.images.swapaxes(0,2)
                input = np.expand_dims(input, 0)
                output = self.model.predict(input)
                # output = np.ones((1, 2048, 2048, 1))
                output = output[0, :, :, 0]
                print('MAX', np.max(output))
            self.images[:-1] = self.images[1:]
            logger.info("Analyser")
            self.hub.new_analysis.emit(output, event, metadata)

        predict_thread = Thread(target=predict)
        predict_thread.start()
