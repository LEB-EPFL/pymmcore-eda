import numpy as np
import ctypes
from ctypes import *
import sys
from smart_scan.dependencies.dwfconstants import *
from enum import IntEnum
import time


class ScanningStragies(IntEnum):
    RASTER = 0
    SNAKE = 1


def mask2active_pixels(
    mask: np.ndarray, scan_strategy: ScanningStragies = ScanningStragies.RASTER
) -> np.ndarray:
    """Coverts a binary mask into a sequence of pixels for which the mask is true.

    Arguments:
    mask -- the binary mask, we skip 0 pixels
    """
    if scan_strategy == ScanningStragies.RASTER:
        active_pixels = np.transpose(np.nonzero(mask))

    elif scan_strategy == ScanningStragies.SNAKE:

        # generate 2 semi-masks with odd and even lines
        semi_mask_1 = np.zeros(mask.shape)
        semi_mask_2 = np.zeros(mask.shape)
        semi_mask_1[::2, :] = mask[::2, :]
        semi_mask_2[1::2, :] = mask[1::2, :]

        pix_1 = np.transpose(np.nonzero(semi_mask_1))
        pix_2 = np.transpose(np.nonzero(semi_mask_2))

        # invert all lines of semi mask 1
        pix_1 = pix_1[np.lexsort((-pix_1[:, 1], pix_1[:, 0]))]

        # concatenate the pixels and sort stably
        active_pixels = np.concatenate((pix_1, pix_2), axis=0)
        active_pixels = active_pixels[active_pixels[:, 0].argsort(kind="stable")]

    return active_pixels


def generate_mask(h: int, w: int, semidim_h: int, semidim_w: int) -> np.ndarray:
    """Generate the binary mask of shape (h,w) with different strategies."""

    # To begin with: ones in the center
    c_w = int(w / 2)
    c_h = int(h / 2)
    semidim_h = semidim_h if (semidim_w < c_w) & (semidim_w < c_h) else min(c_w, c_h)
    semidim_w = semidim_w if (semidim_w < c_w) & (semidim_w < c_h) else min(c_w, c_h)

    mask = np.zeros([h, w])
    mask[c_h - semidim_h : c_h + semidim_h, c_w - semidim_w : c_w + semidim_w] = (
        np.ones([semidim_h * 2, semidim_w * 2])
    )

    # Let's make a cross
    mask[c_h - semidim_w : c_h + semidim_w, c_w - semidim_h : c_w + semidim_h] = (
        np.ones([semidim_w * 2, semidim_h * 2])
    )

    return mask

def normalize_tilewise_vectorized(arr, tile_size):
    """
    Normalize a 2D NumPy array tile-wise to the range [0, 1].
    
    The function divides the array into non-overlapping tiles of the specified size, 
    normalizes each tile independently to the range [0, 1], and recombines them 
    into the original array structure.
    
    Parameters:
    ----------
    arr : np.ndarray
        A 2D NumPy array to be normalized. The array should have numeric values.
    tile_size : int
        The size of each square tile. Both dimensions of the array must be divisible 
        by this value.
    
    Returns:
    -------
    np.ndarray
        A 2D NumPy array of the same shape as `arr`, where each tile is normalized 
        independently to the range [0, 1].
    
    Raises:
    ------
    AssertionError
        If the dimensions of `arr` are not divisible by `tile_size`.
    
    Notes:
    ------
    - Normalization for each tile is performed as:
        normalized_tile = (tile - tile_min) / (tile_max - tile_min)
      where `tile_min` and `tile_max` are the minimum and maximum values within the tile.
    - If `tile_min` equals `tile_max` for a tile (e.g., when all elements in the tile 
      are identical), the corresponding tile in the output will be set to 0 to avoid 
      division by zero.
    - The function assumes no overlap between tiles.
    """
    
    # Get the array shape
    rows, cols = arr.shape
    
    # Ensure the dimensions are divisible by the tile size
    assert rows % tile_size == 0 and cols % tile_size == 0, \
        "Array dimensions must be divisible by the tile size."
    
    # Reshape the array into tiles: (num_tiles_y, tile_size, num_tiles_x, tile_size)
    reshaped = arr.reshape(rows // tile_size, tile_size, cols // tile_size, tile_size)
    
    # Move the tile axes together for simpler broadcasting: (num_tiles_y, num_tiles_x, tile_size, tile_size)
    tiles = reshaped.transpose(0, 2, 1, 3)
    
    # Compute min and max for each tile
    tile_min = tiles.min(axis=(2, 3), keepdims=True)
    tile_max = tiles.max(axis=(2, 3), keepdims=True)
    
    # Avoid division by zero: normalize only where max > min
    normalized_tiles = np.where(
        tile_max > tile_min,
        (tiles - tile_min) / (tile_max - tile_min),
        0
    )
    
    # Reshape back to the original array shape
    normalized_array = normalized_tiles.transpose(0, 2, 1, 3).reshape(rows, cols)
    
    return normalized_array

# def output_voltages_triggered(data_x, data_y, rate, timeout=5):
#     """
#     Outputs two channels with external trigger.
#     """

#     # AnalogOut expects double normalized to +/-1 value
#     def normalize_data(data):
#         dataf = data.astype(np.float64)
#         if np.dtype(data[0]) == np.int8 or np.dtype(data[0]) == np.uint8:
#             dataf /= 128.0
#             dataf -= 1.0
#         elif np.dtype(data[0]) == np.int16:
#             dataf /= 32768.0
#         elif np.dtype(data[0]) == np.uint16:
#             dataf /= 16384.0
#             dataf -= 1
#         elif np.dtype(data[0]) == np.int32:
#             dataf /= 2147483648.0
#         return dataf

#     dataf_x = normalize_data(data_x)
#     data_c_x = (ctypes.c_double * len(dataf_x))(*dataf_x)

#     dataf_y = normalize_data(data_y)
#     data_c_y = (ctypes.c_double * len(dataf_y))(*dataf_y)

#     # Load the DLL
#     if sys.platform.startswith("win"):
#         dwf = cdll.dwf
#     elif sys.platform.startswith("darwin"):
#         dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
#     else:
#         dwf = cdll.LoadLibrary("libdwf.so")

#     # Declare variables
#     hdwf = c_int()
#     channel_x = c_int(0)  # AWG 1
#     channel_y = c_int(1)  # AWG 2

#     # Open the device
#     dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))
#     if hdwf.value == 0:
#         print("Failed to open device")
#         szerr = create_string_buffer(512)
#         dwf.FDwfGetLastErrorMsg(szerr)
#         print(str(szerr.value))
#         quit()

#     dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))  # Manual configuration

#     # Calculate run time
#     sRun = 1.0 * data_x.size / rate

#     # Configure Channel X
#     dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_x, 0, c_int(1))
#     dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_x, 0, c_int(31))  # funcPlay
#     dwf.FDwfAnalogOutRepeatSet(hdwf, channel_x, c_int(1))
#     dwf.FDwfAnalogOutOffsetSet(hdwf, channel_x, c_double(2.5))
#     dwf.FDwfAnalogOutRunSet(hdwf, channel_x, c_double(sRun))
#     dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_x, 0, c_double(rate))
#     dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_x, 0, c_double(2.5))
#     dwf.FDwfAnalogOutTriggerSourceSet(hdwf, channel_x, c_byte(11))  # ExternalTrigger1

#     # Configure Channel Y
#     dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_y, 0, c_int(1))
#     dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_y, 0, c_int(31))  # funcPlay
#     dwf.FDwfAnalogOutRepeatSet(hdwf, channel_y, c_int(1))
#     dwf.FDwfAnalogOutOffsetSet(hdwf, channel_y, c_double(2.5))
#     dwf.FDwfAnalogOutRunSet(hdwf, channel_y, c_double(sRun))
#     dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_y, 0, c_double(rate))
#     dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_y, 0, c_double(2.5))
#     dwf.FDwfAnalogOutTriggerSourceSet(hdwf, channel_y, c_byte(11))  # ExternalTrigger1

#     # Buffer Configuration
#     cBuffer_x = c_int(0)
#     cBuffer_y = c_int(0)

#     dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_x, 0, 0, byref(cBuffer_x))
#     dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_y, 0, 0, byref(cBuffer_y))

#     cBuffer_x.value = min(cBuffer_x.value, data_x.size)
#     cBuffer_y.value = min(cBuffer_y.value, data_y.size)

#     dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_x, 0, data_c_x, cBuffer_x)
#     dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_y, 0, data_c_y, cBuffer_y)

#     # Enable Channels (waiting for trigger)
#     dwf.FDwfAnalogOutConfigure(hdwf, channel_x, c_int(1))
#     dwf.FDwfAnalogOutConfigure(hdwf, channel_y, c_int(1))

#     print("Waiting for trigger...")
#     start_time = time.time()
#     while True:
#         sts = c_ubyte(0)
#         dwf.FDwfAnalogOutStatus(hdwf, channel_x, byref(sts))
#         if sts.value == 3:  # Running state
#             print("Trigger received. Playing waveforms.")
#             break

#         # Check for timeout
#         if time.time() - start_time > timeout:
#             print("Timeout reached while waiting for trigger.")
#             dwf.FDwfAnalogOutReset(hdwf, channel_x)
#             dwf.FDwfAnalogOutReset(hdwf, channel_y)
#             dwf.FDwfDeviceClose(hdwf)
#             return

#     # Wait for playback to finish
#     while True:
#         dwf.FDwfAnalogOutStatus(hdwf, channel_x, byref(sts))
#         if sts.value != 3:  # Not running
#             print("Playback complete.")
#             break

#     # Reset and close
#     dwf.FDwfAnalogOutReset(hdwf, channel_x)
#     dwf.FDwfAnalogOutReset(hdwf, channel_y)
#     dwf.FDwfDeviceClose(hdwf)

# def output_voltages(data_x, data_y, rate):
#     """
#     Adapted from AnalogOut_Play.py
#     DWF Python Example
#     Author:  Digilent, Inc.
#     Revision:  2018-07-19

#     Requires:
#         Python 2.7, 3
#     """
#     # AnalogOut expects double normalized to +/-1 value
#     dataf_x = data_x.astype(np.float64)
#     if np.dtype(data_x[0]) == np.int8 or np.dtype(data_x[0]) == np.uint8:
#         print("Scaling: UINT8")
#         dataf_x /= 128.0
#         dataf_x -= 1.0
#     elif np.dtype(data_x[0]) == np.int16:
#         print("Scaling: INT16")
#         dataf_x /= 32768.0
#     elif np.dtype(data_x[0]) == np.int32:
#         print("Scaling: INT32")
#         dataf_x /= 2147483648.0
#     elif np.dtype(data_x[0]) == np.uint16:
#         print("Scaling: UINT16")
#         dataf_x /= 16384.0
#         dataf_x -= 1.0


#     # prepare the data x
#     data_c_x = (ctypes.c_double * len(dataf_x))(*dataf_x)

#     # AnalogOut expects double normalized to +/-1 value
#     dataf_y = data_y.astype(np.float64)
#     if np.dtype(data_y[0]) == np.int8 or np.dtype(data_y[0]) == np.uint8:
#         print("Scaling: UINT8")
#         dataf_y /= 128.0
#         dataf_y -= 1.0
#     elif np.dtype(data_y[0]) == np.int16:
#         print("Scaling: INT16")
#         dataf_y /= 32768.0
#     elif np.dtype(data_y[0]) == np.int32:
#         print("Scaling: INT32")
#         dataf_y /= 2147483648.0
#     elif np.dtype(data_y[0]) == np.uint16:
#         print("Scaling: UINT16")
#         dataf_y /= 16384.0
#         dataf_y -= 1.0

#     # prepare the data y
#     data_c_y = (ctypes.c_double * len(dataf_y))(*dataf_y)

#     # loads the dll
#     if sys.platform.startswith("win"):
#         dwf = cdll.dwf
#     elif sys.platform.startswith("darwin"):
#         dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
#     else:
#         dwf = cdll.LoadLibrary("libdwf.so")

#     # declare ctype variables
#     hdwf = c_int()
#     channel_x = c_int(0)  # AWG 1
#     channel_y = c_int(1)  # AWG 2

#     # DWF version
#     version = create_string_buffer(16)
#     dwf.FDwfGetVersion(version)

#     # trys to open device
#     dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

#     if hdwf.value == 0:
#         print("Failed to open device")
#         szerr = create_string_buffer(512)
#         dwf.FDwfGetLastErrorMsg(szerr)
#         print(str(szerr.value))
#         quit()

#     # the device will only be configured when FDwf###Configure is called
#     dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))

#     iPlay_x = 0
#     iPlay_y = 0

#     sRun = 1.0 * data_x.size / rate

#     # Set the channel x ?
#     dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_x, 0, c_int(1))
#     dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_x, 0, c_int(31))  # funcPlay
#     dwf.FDwfAnalogOutRepeatSet(hdwf, channel_x, c_int(1))
#     dwf.FDwfAnalogOutOffsetSet(hdwf, channel_x, c_double(2.5)) # output between 0 and 5 V

#     dwf.FDwfAnalogOutRunSet(hdwf, channel_x, c_double(sRun))
#     dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_x, 0, c_double(rate))
#     dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_x, 0, c_double(2.5)) # output between 0 and 5 V

#     # Set the channel Y ?
#     dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_y, 0, c_int(1))
#     dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_y, 0, c_int(31))  # funcPlay
#     dwf.FDwfAnalogOutRepeatSet(hdwf, channel_y, c_int(1))
#     dwf.FDwfAnalogOutOffsetSet(hdwf, channel_y, c_double(2.5))

#     dwf.FDwfAnalogOutRunSet(hdwf, channel_y, c_double(sRun))
#     dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_y, 0, c_double(rate))
#     dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_y, 0, c_double(2.5))

#     # prime the buffers with the first chunk of data
#     cBuffer_x = c_int(0)
#     cBuffer_y = c_int(0)

#     dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_x, 0, 0, byref(cBuffer_x))
#     dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_y, 0, 0, byref(cBuffer_y))

#     if cBuffer_x.value > data_x.size:
#         cBuffer_x.value = data_x.size

#     if cBuffer_y.value > data_y.size:
#         cBuffer_y.value = data_y.size

#     dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_x, 0, data_c_x, cBuffer_x)
#     iPlay_x += cBuffer_x.value
#     dwf.FDwfAnalogOutConfigure(hdwf, channel_x, c_int(1))

#     dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_y, 0, data_c_y, cBuffer_y)
#     iPlay_y += cBuffer_y.value
#     dwf.FDwfAnalogOutConfigure(hdwf, channel_y, c_int(1))

#     dataLost_x = c_int(0)
#     dataFree_x = c_int(0)
#     dataCorrupted_x = c_int(0)
#     dataLost_y = c_int(0)
#     dataFree_y = c_int(0)
#     dataCorrupted_y = c_int(0)
#     sts = c_ubyte(0)
#     totalLost = 0
#     totalCorrupted = 0

#     while True:
#         # fetch analog in info for the channel
#         if (dwf.FDwfAnalogOutStatus(hdwf, channel_x, byref(sts)) != 1) | (
#             dwf.FDwfAnalogOutStatus(hdwf, channel_y, byref(sts)) != 1
#         ):
#             print("Error")
#             szerr = create_string_buffer(512)
#             dwf.FDwfGetLastErrorMsg(szerr)
#             print(szerr.value)
#             break

#         if sts.value != 3:
#             break  # not running !DwfStateRunning

#         if (iPlay_x >= data_x.size) & (iPlay_y >= data_y.size):
#             continue  # no more data to stream

#         dwf.FDwfAnalogOutNodePlayStatus(
#             hdwf,
#             channel_x,
#             0,
#             byref(dataFree_x),
#             byref(dataLost_x),
#             byref(dataCorrupted_x),
#         )
#         dwf.FDwfAnalogOutNodePlayStatus(
#             hdwf,
#             channel_y,
#             0,
#             byref(dataFree_y),
#             byref(dataLost_y),
#             byref(dataCorrupted_y),
#         )

#         totalLost = totalLost + dataLost_x.value + dataLost_y.value
#         totalCorrupted = totalCorrupted + dataCorrupted_x.value + dataCorrupted_y.value

#         if (
#             iPlay_x + dataFree_x.value > data_x.size
#         ):  # last chunk might be less than the free buffer size
#             dataFree_x.value = data_x.size - iPlay_x

#         if (
#             iPlay_y + dataFree_y.value > data_y.size
#         ):  # last chunk might be less than the free buffer size
#             dataFree_y.value = data_y.size - iPlay_y

#         if (dataFree_x.value == 0) & (dataFree_y.value == 0):
#             continue

#         if (
#             dwf.FDwfAnalogOutNodePlayData(
#                 hdwf, channel_x, 0, byref(data_c_x, iPlay_x * 8), dataFree_x
#             )
#             != 1
#         ) | (
#             dwf.FDwfAnalogOutNodePlayData(
#                 hdwf, channel_y, 0, byref(data_c_y, iPlay_y * 8), dataFree_y
#             )
#             != 1
#         ):  # offset for double is *8 (bytes)
#             print("Error")
#             break

#         iPlay_x += dataFree_x.value
#         iPlay_y += dataFree_y.value

#     # Resets the outputs
#     dwf.FDwfAnalogOutReset(hdwf, channel_x)
#     dwf.FDwfAnalogOutReset(hdwf, channel_y)

#     # Close the device
#     dwf.FDwfDeviceClose(hdwf)

# def pixels2voltages(
#     pixel_sequence: np.ndarray, m_w: float, m_h: float, a_w: float, a_h: float
# ) -> np.ndarray:
#     """
#     Converts pixel coordinates to voltages [mV], assuming a linear relation.
#     Voltage = m * pixel_coordinate + a
#     """
#     pixel_sequence = np.transpose(pixel_sequence)

#     m = np.zeros(pixel_sequence.shape)
#     m[:][0] = m_h
#     m[:][1] = m_w

#     a = np.zeros(pixel_sequence.shape)
#     a[:][0] = a_h
#     a[:][1] = a_w

#     voltage_sequence = pixel_sequence * m + a

#     return np.transpose(voltage_sequence)
