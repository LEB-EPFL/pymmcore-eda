from __future__ import annotations

import time
from threading import Thread
from typing import TYPE_CHECKING

import numpy as np
from useq import MDAEvent

from src.pymmcore_eda._logger import logger

if TYPE_CHECKING:
    from typing import Any

    from pymmcore_plus.metadata import FrameMetaV1

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
    """Settings for the Analyser."""

    n_frames_model: int = 4
    n_fake_predictions: int = (
        3  # number of initial fake predictions. The first ones are always longer
    )
    tile_size: int = 256  # used for tile-wise normalisation.
    crop_size: int = (
        512  # crop the images before feeding the model. Used to haste inference.
    )
    image_shape: tuple = (2048, 2048)

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
    meta: FrameMetaV1 = {
        "mda_event": fake_event,
        "format": "frame-dict",
        "version": "1.0",
        "pixel_size_um": event.metadata.get("pixel_size_um", 0.1),
        "camera_device": event.metadata.get("camera_device", "Camera"),
        "exposure_ms": event.metadata.get("exposure", 100),
        "property_values": event.metadata.get("property_values", {}),
        "runner_time_ms": event.metadata.get("runner_time_ms", 0),
    }

    hub.new_writer_frame.emit(output_save, fake_event, meta)


class Dummy_Analyser:
    """Analyse the image and produce a map for the interpreter."""

    def __init__(self, hub: EventHub, prediction_time: float = 0.2):
        self.hub: EventHub = hub
        self.hub.frameReady.connect(self._analyse)
        self.prediction_time: float = prediction_time
        self.predict_thread: Thread | None = None

    def _analyse(self, img: np.ndarray, event: MDAEvent, metadata: dict) -> None:
        """Perform the analysis on the image and emit the result."""
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


def dummy_predict(
    img: np.ndarray,
    event: MDAEvent,
    metadata: dict[str, Any],
    hub: EventHub,
    prediction_time: float,
) -> None:
    """Perform a dummy prediction on the image."""
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
        f"Dummy prediction finished for event t = {t}. Duration = {elapsed} ms."
        "Max value: {np.max(output):.2f}"
    )

    # Emit the event score
    hub.new_analysis.emit(output, event, metadata)

    # Emit new_writer_frame to store the network output
    emit_writer_signal(hub, event, output)
