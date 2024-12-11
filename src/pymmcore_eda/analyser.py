from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from tifffile import imread
from pathlib import Path
from tensorflow import keras
import tensorflow as tf

from pymmcore_eda._logger import logger

if TYPE_CHECKING:
    import numpy as np
    from event_hub import EventHub
    from useq import MDAEvent

class AnalyserSettings:
    model_path: str = "//sb-nas1.rcp.epfl.ch/leb/Scientific_projects/deep_events_WS/data/original_data/training_data/20240826_1134_brightfield_cos7_n3_f1/20240826_1134_0_model.h5"

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
        # load model
        self.model = keras.models.load_model(settings.model_path)
        print("Model loaded")
        self.images = np.zeros((3, 2048, 2048))

        self.dummy_data = imread(Path("C:/Users/kasia/Desktop/epfl/stk_0010_FOV_1_MMStack_Default.ome.tif"))

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        if event.index.get("c", 0) != 0:
            return
        img = self.dummy_data[event.index.get("t", 0)]
        self.images[-1] = img
        if event.index.get("t", 0) < 2:
            return
        else:
            input = self.images.swapaxes(0,2)
            input = np.expand_dims(input, 0)
            output = self.model.predict(input)
            output = output[0, :, :, 0]
            #print('MAX', np.max(output))
        self.images[:-1] = self.images[1:]
        logger.info("Analyser")
        self.hub.new_analysis.emit(output, event, metadata)
