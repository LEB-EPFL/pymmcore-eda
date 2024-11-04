import numpy as np
import ctypes
from ctypes import *
import sys


def mask2active_pixels(mask: np.ndarray) -> None:
    """Coverts a binary mask into a sequence of pixels for which the mask is true.

    Arguments:
    mask -- the binary mask, we skip 0 pixels
    """
    active_pixels = np.transpose(np.nonzero(mask))
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


def output_voltages(data_x, data_y, rate):
    """
    Adapted from AnalogOut_Play.py
    DWF Python Example
    Author:  Digilent, Inc.
    Revision:  2018-07-19

    Requires:
        Python 2.7, 3
    """
    # AnalogOut expects double normalized to +/-1 value
    dataf_x = data_x.astype(np.float64)
    if np.dtype(data_x[0]) == np.int8 or np.dtype(data_x[0]) == np.uint8:
        print("Scaling: UINT8")
        dataf_x /= 128.0
        dataf_x -= 1.0
    elif np.dtype(data_x[0]) == np.int16:
        print("Scaling: INT16")
        dataf_x /= 32768.0
    elif np.dtype(data_x[0]) == np.int32:
        print("Scaling: INT32")
        dataf_x /= 2147483648.0

    # prepare the data x
    data_c_x = (ctypes.c_double * len(dataf_x))(*dataf_x)

    # AnalogOut expects double normalized to +/-1 value
    dataf_y = data_y.astype(np.float64)
    if np.dtype(data_x[0]) == np.int8 or np.dtype(data_x[0]) == np.uint8:
        print("Scaling: UINT8")
        dataf_y /= 128.0
        dataf_y -= 1.0
    elif np.dtype(data_x[0]) == np.int16:
        print("Scaling: INT16")
        dataf_y /= 32768.0
    elif np.dtype(data_x[0]) == np.int32:
        print("Scaling: INT32")
        dataf_y /= 2147483648.0

    # prepare the data y
    data_c_y = (ctypes.c_double * len(dataf_y))(*dataf_y)

    # loads the dll
    if sys.platform.startswith("win"):
        dwf = cdll.dwf
    elif sys.platform.startswith("darwin"):
        dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
    else:
        dwf = cdll.LoadLibrary("libdwf.so")

    # declare ctype variables
    hdwf = c_int()
    channel_x = c_int(0)  # AWG 1
    channel_y = c_int(1)  # AWG ?

    # DWF version
    version = create_string_buffer(16)
    dwf.FDwfGetVersion(version)

    # trys to open device
    dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

    if hdwf.value == 0:
        print("Failed to open device")
        szerr = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(szerr)
        print(str(szerr.value))
        quit()

    # the device will only be configured when FDwf###Configure is called
    dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))

    iPlay_x = 0
    iPlay_y = 0

    sRun = 1.0 * data_x.size / rate

    # Set the channel x ?
    dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_x, 0, c_int(1))
    dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_x, 0, c_int(31))  # funcPlay
    dwf.FDwfAnalogOutRepeatSet(hdwf, channel_x, c_int(5))
    dwf.FDwfAnalogOutOffsetSet(hdwf, channel_x, c_double(2.5))

    dwf.FDwfAnalogOutRunSet(hdwf, channel_x, c_double(sRun))
    dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_x, 0, c_double(rate))
    dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_x, 0, c_double(1))

    # Set the channel Y ?
    dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_y, 0, c_int(1))
    dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_y, 0, c_int(31))  # funcPlay
    dwf.FDwfAnalogOutRepeatSet(hdwf, channel_y, c_int(5))
    dwf.FDwfAnalogOutOffsetSet(hdwf, channel_y, c_double(1.0))

    dwf.FDwfAnalogOutRunSet(hdwf, channel_y, c_double(sRun))
    dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_y, 0, c_double(rate))
    dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_y, 0, c_double(1))

    # prime the buffers with the first chunk of data
    cBuffer_x = c_int(0)
    cBuffer_y = c_int(0)

    dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_x, 0, 0, byref(cBuffer_x))
    dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_y, 0, 0, byref(cBuffer_y))

    if cBuffer_x.value > data_x.size:
        cBuffer_x.value = data_x.size

    if cBuffer_y.value > data_y.size:
        cBuffer_y.value = data_y.size

    dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_x, 0, data_c_x, cBuffer_x)
    iPlay_x += cBuffer_x.value
    dwf.FDwfAnalogOutConfigure(hdwf, channel_x, c_int(1))

    dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_y, 0, data_c_y, cBuffer_y)
    iPlay_y += cBuffer_y.value
    dwf.FDwfAnalogOutConfigure(hdwf, channel_y, c_int(1))

    dataLost_x = c_int(0)
    dataFree_x = c_int(0)
    dataCorrupted_x = c_int(0)
    dataLost_y = c_int(0)
    dataFree_y = c_int(0)
    dataCorrupted_y = c_int(0)
    sts = c_ubyte(0)
    totalLost = 0
    totalCorrupted = 0

    while True:
        # fetch analog in info for the channel
        if (dwf.FDwfAnalogOutStatus(hdwf, channel_x, byref(sts)) != 1) | (
            dwf.FDwfAnalogOutStatus(hdwf, channel_y, byref(sts)) != 1
        ):
            print("Error")
            szerr = create_string_buffer(512)
            dwf.FDwfGetLastErrorMsg(szerr)
            print(szerr.value)
            break

        if sts.value != 3:
            break  # not running !DwfStateRunning

        if (iPlay_x >= data_x.size) & (iPlay_y >= data_y.size):
            continue  # no more data to stream

        dwf.FDwfAnalogOutNodePlayStatus(
            hdwf,
            channel_x,
            0,
            byref(dataFree_x),
            byref(dataLost_x),
            byref(dataCorrupted_x),
        )
        dwf.FDwfAnalogOutNodePlayStatus(
            hdwf,
            channel_y,
            0,
            byref(dataFree_y),
            byref(dataLost_y),
            byref(dataCorrupted_y),
        )

        totalLost = totalLost + dataLost_x.value + dataLost_y.value
        totalCorrupted = totalCorrupted + dataCorrupted_x.value + dataCorrupted_y.value

        if (
            iPlay_x + dataFree_x.value > data_x.size
        ):  # last chunk might be less than the free buffer size
            dataFree_x.value = data_x.size - iPlay_x

        if (
            iPlay_y + dataFree_y.value > data_y.size
        ):  # last chunk might be less than the free buffer size
            dataFree_y.value = data_y.size - iPlay_y

        if (dataFree_x.value == 0) & (dataFree_y.value == 0):
            continue

        if (
            dwf.FDwfAnalogOutNodePlayData(
                hdwf, channel_x, 0, byref(data_c_x, iPlay_x * 8), dataFree_x
            )
            != 1
        ) | (
            dwf.FDwfAnalogOutNodePlayData(
                hdwf, channel_y, 0, byref(data_c_y, iPlay_y * 8), dataFree_y
            )
            != 1
        ):  # offset for double is *8 (bytes)
            print("Error")
            break

        iPlay_x += dataFree_x.value
        iPlay_y += dataFree_y.value

    # Resets the outputs
    dwf.FDwfAnalogOutReset(hdwf, channel_x)
    dwf.FDwfAnalogOutReset(hdwf, channel_y)

    # Close the device
    dwf.FDwfDeviceClose(hdwf)


def pixel2voltage(pixel_sequence, m_w: float, m_h: float, a_w: float, a_h: float):
    """
    Converts pixel coordinates to voltages, assuming a linear relation.
    Voltage = m * pixel_coordinate + a
    """
    pixel_sequence = np.transpose(pixel_sequence)

    m = np.zeros(pixel_sequence.shape)
    m[:][0] = m_h
    m[:][1] = m_w

    a = np.zeros(pixel_sequence.shape)
    a[:][0] = a_h
    a[:][1] = a_w

    voltage_sequence = pixel_sequence * m + a

    return np.transpose(voltage_sequence)
