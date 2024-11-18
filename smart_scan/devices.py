from abc import ABC, abstractmethod
from smart_scan.settings.instrumentSettings import instrumentSettings
from smart_scan.helpers import loggingHelper
from smart_scan.resources import logStrings
import numpy as np
import sys
from ctypes import *
import ctypes

logger = loggingHelper.createLogger(loggerName=__name__)


class Device(ABC):
    """This is the superclass for all the hardware devices to be connected with the software."""

    ID: int  # how to impose properties to subclass

    @abstractmethod
    def connect(self):
        """Enstablish the connection with the device"""

    @abstractmethod
    def disconnect(self):
        """Close the connection with the device"""

    @abstractmethod
    def isConnected(self):
        """Returns the connection status"""


class Galvo_Scanners(Device):
    """This is the class for the galvanometric mirrors used to perform (smart) scans."""

    def __init__(self) -> None:
        self._isConnected = False
        self._calibration = instrumentSettings.galvo_calibration
        self._dwf = None
        self._hdwf = None
        self._channel_x = None
        self._channel_y = None

    @property
    def calibration(self):
        return self._calibration

    ##########################
    ####  Public methods ####
    ##########################

    def connect(self):
        """Connects the galvo mirror system."""
        if not self.isConnected():
            try:
                self._dwf, self._hdwf, self._channel_x, self._channel_y = (
                    self._connect()
                )
                self._isConnected = True

            except RuntimeError:
                loggingHelper.displayMessage(logStrings.GALVO_1)
                logger.error(logStrings.GALVO_1)

    def disconnect(self):
        """Disconnects the galvo mirror system."""
        if self.isConnected():
            try:
                self._disconnect()
                self._isConnected = False
            except:
                return

    def isConnected(self) -> bool:
        """Returns the connection status of the galvo systems."""
        return self._isConnected

    def scan(self, voltage_x, voltage_y, rate):

        if not self.isConnected():
            logger.error(logStrings.GALVO_2)
        else:
            n_voltage_x = self._norm_signal(voltage_x)
            n_voltage_y = self._norm_signal(voltage_y)

            self._scan(voltage_x, voltage_y, n_voltage_x, n_voltage_y, rate)

    ##########################
    ####  Private methods ####
    ##########################

    def _norm_signal(self, voltage):
        """Normalises and prepare the signal to be later ouputted."""
        voltage_f = voltage.astype(np.float64)
        if np.dtype(voltage[0]) == np.int8 or np.dtype(voltage[0]) == np.uint8:
            print("Scaling: UINT8")
            voltage_f /= 128.0
            voltage_f -= 1.0
        elif np.dtype(voltage[0]) == np.int16:
            print("Scaling: INT16")
            voltage_f /= 32768.0
        elif np.dtype(voltage[0]) == np.int32:
            print("Scaling: INT32")
            voltage_f /= 2147483648.0

        # prepare the data x
        return (ctypes.c_double * len(voltage_f))(*voltage_f)

    def _scan(self, data_x, data_y, data_c_x, data_c_y, rate):
        """
        Adapted from AnalogOut_Play.py
        DWF Python Example
        Author:  Digilent, Inc.
        Revision:  2018-07-19

        Requires:
            Python 2.7, 3
        """
        dwf = self._dwf
        hdwf = self._hdwf
        channel_x = self._channel_x
        channel_y = self._channel_y

        # the device will only be configured when FDwf###Configure is called
        dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))

        iPlay_x = 0
        iPlay_y = 0

        sRun = 1.0 * data_x.size / rate

        # Set the channel x ?
        dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_x, 0, c_int(1))
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_x, 0, c_int(31))  # funcPlay
        dwf.FDwfAnalogOutRepeatSet(hdwf, channel_x, c_int(1))

        dwf.FDwfAnalogOutRunSet(hdwf, channel_x, c_double(sRun))
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_x, 0, c_double(rate))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_x, 0, c_double(1.0))

        # Set the channel Y ?
        dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_y, 0, c_int(1))
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_y, 0, c_int(31))  # funcPlay
        dwf.FDwfAnalogOutRepeatSet(hdwf, channel_y, c_int(1))

        dwf.FDwfAnalogOutRunSet(hdwf, channel_y, c_double(sRun))
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_y, 0, c_double(rate))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_y, 0, c_double(1.0))

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
            totalCorrupted = (
                totalCorrupted + dataCorrupted_x.value + dataCorrupted_y.value
            )

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

    def _connect(self) -> tuple:
        """Connects the galvo mirror system, and return objects needed for the scan"""
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
        channel_y = c_int(1)  # AWG 2

        # DWF version
        version = create_string_buffer(16)
        dwf.FDwfGetVersion(version)

        # trys to open device
        dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

        if hdwf.value == 0:
            szerr = create_string_buffer(512)
            dwf.FDwfGetLastErrorMsg(szerr)
            raise (RuntimeError)

        return (dwf, hdwf, channel_x, channel_y)

    def _disconnect(self):
        """Disconnects the galvo mirror system."""

        # Resets the outputs
        self._dwf.FDwfAnalogOutReset(self._hdwf, self._channel_x)
        self._dwf.FDwfAnalogOutReset(self._hdwf, self._channel_y)

        # Close the device
        self._dwf.FDwfDeviceClose(self._hdwf)
