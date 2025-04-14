from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING

import numpy as np
from pymmcore_plus.metadata.schema import FrameMetaV1
from useq import MDAEvent

from src.pymmcore_eda._logger import logger
from src.pymmcore_eda.helpers.function_helpers import normalize_tilewise_vectorized

if TYPE_CHECKING:
    from tensorflow import keras

    from pymmcore_eda.event_hub import EventHub


class CropLimits:
    """Class to define the crop limits for the image."""

    def __init__(self, image_shape: tuple, crop_size: int):
        H, W = image_shape
        crop_size = min(crop_size, H, W)  # Restrict size if too large

        # Compute center coordinates
        center_y, center_x = H // 2, W // 2
        half_side = crop_size // 2

        # Define mask boundaries
        self.y_start, self.y_end = (
            max(0, center_y - half_side),
            min(H, center_y + half_side),
        )
        self.x_start, self.x_end = (
            max(0, center_x - half_side),
            min(W, center_x + half_side),
        )


class AnalyserSettings:
<<<<<<< HEAD
    """Settings for the Analyser."""

    model_path: str = (
        "//sb-nas1.rcp.epfl.ch/LEB/Scientific_projects/deep_events_WS/data"
        "original_data/training_data/20240224_0205_brightfield_cos7_n5_f1/20240224_0208_model.h5"
    )
    # model_path: str = ("/Volumes/LEB/Scientific_projects/deep_events_WS/data/",
    # "original_data/training_data/20240224_0205_brightfield_cos7_n5_f1/",
    # "20240224_0208_model.h5")
    n_frames_model = 4
    n_fake_predictions = (
        3  # number of initial fake predictions. The first ones are always longer
    )
    tile_size = 256  # used for tile-wise normalisation.
    crop_size = (
        512  # crop the images before feeding the model. Used to haste inference.
    )
    image_shape = (2048, 2048)

=======
    
    n_frames_model: int = 4
    n_fake_predictions: int = 3      # number of initial fake predictions. The first ones are always longer
    tile_size: int = 256 # used for tile-wise normalisation.
    crop_size: int = 512 # crop the images before feeding the model. Used to haste inference. 
    image_shape: tuple = (2048,2048)
    
>>>>>>> b880f23 (Deleted references to smart_scan, and viewer.)
    # Calculated properties
    crop_limits = CropLimits(image_shape, crop_size)


def emit_writer_signal(
    hub: EventHub, event: MDAEvent, output: np.ndarray, custom_channel: int = 2
) -> None:
    """
    Emit the new_writer_frame signal.

    Parameters
    ----------
    hub (EventHub): The event hub to emit the signal.
    event (MDAEvent): The event containing t_index and metadata about the frame.
    output (np.ndarray): The output data to be emitted.
    custom_channel (int, optional): The custom channel index. Defaults to 2.
    """
    t_index = event.index.get("t", 0)

    fake_event = MDAEvent(
        channel=event.channel,
        index={"t": t_index, "c": custom_channel},
        min_start_time=0,
    )

    output_save = np.array(output * 1e4)

    # output_save[0:256, 0:256] = 500

    output_save = np.transpose(output_save)
    output_save = output_save.astype("uint16")
    meta = FrameMetaV1(fake_event)  # type: ignore

    hub.new_writer_frame.emit(output_save, fake_event, meta)


class Dummy_Analyser:
    """Analyse the image and produce a map for the interpreter."""

    def __init__(self, hub: EventHub, prediction_time: float = 0.2):
        self.hub = hub
        self.hub.frameReady.connect(self._analyse)
        self.prediction_time = prediction_time
        self.predict_thread: None | Thread = None

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict) -> None:
        if event.index.get("c", 0) != 0:
            return

        # Allows only one prediction thread at a time
        if self.predict_thread is None or not self.predict_thread.is_alive():
            # Perform the prediction in a separate thread
            predict_thread = Thread(
                target=dummy_predict,
                args=(img.copy(), event, metadata, self.hub, self.prediction_time),
            )

            predict_thread.start()

            # Store the thread to avoid spawning multiple threads
            self.predict_thread = predict_thread


class Analyser:
    """Analyse the image and produce an event score map for the interpreter."""

<<<<<<< HEAD
    def __init__(self, hub: EventHub):
        # Import tensorflow here, so that we don't need to do it when
        # using DummyAnalyser
=======
    def __init__(self, hub: EventHub, model_path : str = None):
        
        # Import tensorflow here, so that we don't need to do it when using DummyAnalyser
>>>>>>> b880f23 (Deleted references to smart_scan, and viewer.)
        from tensorflow import keras

        settings = AnalyserSettings()

        self.hub = hub
<<<<<<< HEAD
        self.model = keras.models.load_model(settings.model_path, compile=False)
=======
        self.model = keras.models.load_model(model_path, compile = False)
>>>>>>> b880f23 (Deleted references to smart_scan, and viewer.)
        self.n_frames_model = settings.n_frames_model
        self.predict_thread: None | Thread = None
        self.output = np.zeros(settings.image_shape)
        self.tile_size = settings.tile_size
        self.n_fake_predictions = settings.n_fake_predictions

        # Obtain the crop limits
        self.crop_limits = settings.crop_limits

        # connect the frameReady signal to the analyse method
        self.hub.frameReady.connect(self._analyse)
<<<<<<< HEAD

        self.images = np.zeros((self.n_frames_model + 1, *settings.image_shape))
        # self.dummy_data = imread(Path("C:/Users/glinka/Desktop
        # stk_0010_FOV_1_MMStack_Default.ome.tif"))
        # img = self.dummy_data[0:3]
=======
        
        self.images = np.zeros((self.n_frames_model+1, *settings.image_shape))
>>>>>>> b880f23 (Deleted references to smart_scan, and viewer.)

        # Perform a few first fake predictions - it takes a long time
        img = self.images
        input_img = img.swapaxes(0, 2)
        input_img = np.expand_dims(input_img, 0)
        input_cropped = input_img[
            :,
            self.crop_limits.y_start : self.crop_limits.y_end,
            self.crop_limits.x_start : self.crop_limits.x_end,
            :,
        ]
        for _ in range(self.n_fake_predictions):
            self.model.predict(input_cropped)
<<<<<<< HEAD

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict) -> None:
=======
        
    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict):
        
>>>>>>> b880f23 (Deleted references to smart_scan, and viewer.)
        # Skip if not the first channel
        if event.index.get("c", 0) != 0:
            return

        # tile-wise normalisation of the image
        try:
            img = normalize_tilewise_vectorized(arr=img, tile_size=self.tile_size)
        except AssertionError as e:
            img = np.divide(img, np.max(img))
            logger.info(
                f"Analyser: failed to perform tile-wise normalisation."
                f"{e}. Normalising the whole image instead."
            )

        # For test, use dummy data
        # self.img = self.dummy_data[self.event.index.get("t", 0)]

        # Add the current image to the list of images
        self.images[-1] = img

        # Allows only one prediction thread at a time
        if self.predict_thread is None or not self.predict_thread.is_alive():
            t_index = event.index.get("t", 0)

            # Perform the prediction in a separate thread
            predict_thread = Thread(
                target=predict,
                args=(
                    self.images.copy(),
                    t_index,
                    event,
                    self.model,
                    self.hub,
                    metadata,
                    self.n_frames_model,
                    self.output,
                    self.crop_limits,
                ),
            )

            # Store the thread to avoid spawning multiple threads
            self.predict_thread = predict_thread

            predict_thread.start()

        # Shift the images in the list
        self.images[:-1] = self.images[1:]


def dummy_predict(
    img: np.ndarray,
    event: MDAEvent,
    metadata: dict,
    hub: EventHub,
    prediction_time: float,
) -> None:
    """Dummy for needing tensorflow to run the analyser."""
    # Determine the maximum possible value based on dtype
    dtype = img.dtype
    max_value = 1
    if np.issubdtype(dtype, np.integer):
        max_value = np.iinfo(dtype).max
    elif np.issubdtype(dtype, np.floating):
        max_value = np.finfo(dtype).max

    # normalise the image
    output = img / max_value

    # Sleep for a while to simulate the prediction time
    t_start = time.time()
    time.sleep(prediction_time)
    elapsed = int((time.time() - t_start) * 1000)
    t = event.index.get("t", 0)
    logger.info(
        f"""Dummy prediction finished for event t = {t}.
          Duration = {elapsed} ms. Max value: {np.max(output):.2f}"""
    )

    # Emit the event score
    hub.new_analysis.emit(output, event, metadata)

    # Emit new_writer_frame to store the network output
    emit_writer_signal(hub, event, output)


def predict(
    images: np.ndarray,
    t_index: int,
    event: MDAEvent,
    model: keras.Model,
    hub: EventHub,
    metadata: dict,
    n_frames_model: int,
    output: np.ndarray,
    crop_limits: CropLimits,
) -> None:
    """Run model on images."""
    # Skip if the list of images is not full
    if event.index.get("t", 0) < n_frames_model:
        return

    input_img = images.swapaxes(0, 2)
    input_img = np.expand_dims(input_img, 0)
    input_cropped = input_img[
        :,
        crop_limits.y_start : crop_limits.y_end,
        crop_limits.x_start : crop_limits.x_end,
        :,
    ]

    # Perform and time the prediction
    t_start = time.time()
    output_cropped = model.predict(input_cropped)
    elapsed = int((time.time() - t_start) * 1000)
    logger.info(
        f"""Prediction finished for event t = {t_index}.
        Duration = {elapsed} ms. Max value: {np.max(output_cropped):.2f}"""
    )

    output_cropped = output_cropped[0, :, :, 0]
    output[
        crop_limits.y_start : crop_limits.y_end, crop_limits.x_start : crop_limits.x_end
    ] = output_cropped

    # Emits new_analysis signal
    hub.new_analysis.emit(output, event, metadata)

    # Emits new_writer_frame signal to store the network output
    emit_writer_signal(hub, event, output)
