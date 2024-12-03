from abc import ABC, abstractmethod
from smart_scan.settings.instrumentSettings import instrumentSettings
from smart_scan.helpers import loggingHelper
from smart_scan.helpers.function_helpers import ScanningStragies, mask2active_pixels

from smart_scan.resources import logStrings
import numpy as np
import sys
from ctypes import *
import ctypes
import time

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
        self._dwf = None
        self._hdwf = None
        self._channel_x = None
        self._channel_y = None
        self._calibration = instrumentSettings().galvo_calibration
        self._maxV = instrumentSettings().galvo_maxV
        self._minV = instrumentSettings().galvo_minV


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

    
    def scan(self, mask:np.ndarray, pixelsize:float, scan_strategy:ScanningStragies, duration:float):
        """Performs a scan of the non_zero pixels in mask, with the selected scanning strategy and duration [s].
        
        Input: 
        mask:           2D numpy array
        pixelsize:      the size of the mask's pixels [µm]
        scan_strategy:  the desired scanning strategy, from the class ScanningStragies 
        duration:       the duration of the scan [s]."""
        
        if not self.isConnected():
            logger.error(logStrings.GALVO_2)
        
        else:
            max_voltage = self._maxV * 1000 #[mv]
            min_voltage = self._minV * 1000 #[mv]

            # Extract the non-zero values from the mask
            scan_pixels = mask2active_pixels( mask=mask, scan_strategy=scan_strategy)
            
            # Converts the pixels of the mask in voltages for the output
            scan_voltages = self._pixels2voltages(scan_pixels, pixelsize)
            
            # Limits Voltages in the range [min_voltage max_voltage], and normalizes the voltages so that max_voltage == 2**15-1
            voltages_x = np.transpose(scan_voltages)[0].copy()
            voltages_x = self._limit_voltage(voltage=voltages_x, min_v=min_voltage, max_v=max_voltage)
            voltages_x *= (2**15-1)/max_voltage
            voltages_x = np.uint16(voltages_x)
            
            voltages_y = np.transpose(scan_voltages)[1].copy()
            voltages_y = self._limit_voltage(voltage=voltages_y, min_v=min_voltage, max_v=max_voltage)
            voltages_y *= (2**15-1)/max_voltage
            voltages_y = np.uint16(voltages_y)

            # Diligent AnalogOut expects double normalized to +/-1 value
            n_voltage_x = self._norm_voltage(voltages_x)
            n_voltage_y = self._norm_voltage(voltages_y)

            # Compute the rate
            n_samples = len(voltages_x)
            rate = n_samples/duration # Hz
            
            # Ouputs the voltages
            self._ouput_voltages(voltages_x, voltages_y, n_voltage_x, n_voltage_y, rate)

    def scan_triggered(self, mask:np.ndarray, pixelsize:float, scan_strategy:ScanningStragies, duration:float):
        """Performs a triggered scan of the non_zero pixels in mask, with the selected scanning strategy and duration [s].
        
        Input: 
        mask:           2D numpy array
        pixelsize:      the size of the mask's pixels [µm]
        scan_strategy:  the desired scanning strategy, from the class ScanningStragies 
        duration:       the duration of the scan [s]."""


        if not self.isConnected():
            logger.error(logStrings.GALVO_2)
        
        else:
            max_voltage = self._maxV * 1000 #[mv]
            min_voltage = self._minV * 1000 #[mv]

            # Extract the non-zero values from the mask
            scan_pixels = mask2active_pixels( mask, scan_strategy)
            
            # Converts the pixels in voltages for the output
            scan_voltages = self._pixels2voltages(scan_pixels, pixelsize)
            
            # Limits Voltages in the range [min_voltage max_voltage], and normalizes the voltages so that max_voltage == 2**15-1
            voltages_x = np.transpose(scan_voltages)[0].copy()
            voltages_x = self._limit_voltage(voltage=voltages_x, min_v=min_voltage, max_v=max_voltage)
            voltages_x *= (2**15-1)/max_voltage
            voltages_x = np.uint16(voltages_x)
            
            voltages_y = np.transpose(scan_voltages)[1].copy()
            voltages_y = self._limit_voltage(voltage=voltages_y, min_v=min_voltage, max_v=max_voltage)
            voltages_y *= (2**15-1)/max_voltage
            voltages_y = np.uint16(voltages_y)

            # Diligent AnalogOut expects double normalized to +/-1 value
            n_voltage_x = self._norm_voltage(voltages_x)
            n_voltage_y = self._norm_voltage(voltages_y)

            # Compute the rate
            n_samples = len(voltages_x)
            rate = n_samples/duration # Hz
            
            # Ouputs the voltages
            self._ouput_voltages_trg(voltages_x, voltages_y, n_voltage_x, n_voltage_y, rate)
    
    
    ##########################
    ####  Private methods ####
    ##########################
    def _limit_voltage(self, voltage:np.ndarray, min_v:float, max_v:float) -> np.ndarray:
        """Limits the voltage array in the range [min_v, max_v]."""
        voltage[voltage>=max_v] = max_v
        voltage[voltage<=min_v] = min_v
        return voltage

    def _pixels2voltages(self,pixel_sequence: np.ndarray, pixelsize:float) -> np.ndarray:
        """
        Converts pixel coordinates to voltages [mV], assuming a linear relation.
        Voltage = m * pixel_coordinate*pixelsize + a
        """
        pixel_sequence = np.transpose(pixel_sequence)

        m = np.zeros(pixel_sequence.shape)
        a = np.zeros(pixel_sequence.shape)
        m[:][0] = self._calibration['m_y']
        m[:][1] = self._calibration['m_x']
        a[:][0] = self._calibration['a_y']
        a[:][1] = self._calibration['a_x']

        voltage_sequence = pixel_sequence * pixelsize * m + a

        return np.transpose(voltage_sequence)
    
    def _norm_voltage(self, voltage):
        """Normalises and prepare the voltage to be later ouputted."""
        voltage_f = voltage.astype(np.float64)
        if np.dtype(voltage[0]) == np.int8 or np.dtype(voltage[0]) == np.uint8:
            print("Scaling: UINT8")
            voltage_f /= 128.0
            voltage_f -= 1.0
        elif np.dtype(voltage[0]) == np.int16:
            print("Scaling: INT16")
            voltage_f /= 32768.0
        elif np.dtype(voltage[0]) == np.uint16:
            print("Scaling: UINT16")
            voltage_f /= 16384.0
            voltage_f -= 1.0
        elif np.dtype(voltage[0]) == np.int32:
            print("Scaling: INT32")
            voltage_f /= 2147483648.0
        
        return (ctypes.c_double * len(voltage_f))(*voltage_f)

    def _ouput_voltages(self, data_x, data_y, data_c_x, data_c_y, rate):
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
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_x, 0, c_double(2.5))
        dwf.FDwfAnalogOutOffsetSet(hdwf, channel_x, c_double(2.5)) # output between 0 and 5 V
        dwf.FDwfAnalogOutTriggerSourceSet(hdwf, channel_x, c_byte(0))  # No trigger


        # Set the channel Y ?
        dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_y, 0, c_int(1))
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_y, 0, c_int(31))  # funcPlay
        dwf.FDwfAnalogOutRepeatSet(hdwf, channel_y, c_int(1))

        dwf.FDwfAnalogOutRunSet(hdwf, channel_y, c_double(sRun))
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_y, 0, c_double(rate))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_y, 0, c_double(2.5))
        dwf.FDwfAnalogOutOffsetSet(hdwf, channel_y, c_double(2.5)) # output between 0 and 5 V
        dwf.FDwfAnalogOutTriggerSourceSet(hdwf, channel_y, c_byte(0))  # No trigger


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

    def _ouput_voltages_trg(self, voltage_x, voltage_y, n_voltage_x, n_voltage_y, rate):
        
        dwf = self._dwf
        hdwf = self._hdwf
        channel_x = self._channel_x
        channel_y = self._channel_y

        dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))  # Manual configuration

        # Calculate run time
        sRun = 1.0 * voltage_x.size / rate

        # Configure Channel X
        dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_x, 0, c_int(1))
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_x, 0, c_int(31))  # funcPlay
        dwf.FDwfAnalogOutRepeatSet(hdwf, channel_x, c_int(1))
        dwf.FDwfAnalogOutOffsetSet(hdwf, channel_x, c_double(2.5))
        dwf.FDwfAnalogOutRunSet(hdwf, channel_x, c_double(sRun))
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_x, 0, c_double(rate))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_x, 0, c_double(2.5))
        dwf.FDwfAnalogOutTriggerSourceSet(hdwf, channel_x, c_byte(11))  # ExternalTrigger1

        # Configure Channel Y
        dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_y, 0, c_int(1))
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_y, 0, c_int(31))  # funcPlay
        dwf.FDwfAnalogOutRepeatSet(hdwf, channel_y, c_int(1))
        dwf.FDwfAnalogOutOffsetSet(hdwf, channel_y, c_double(2.5))
        dwf.FDwfAnalogOutRunSet(hdwf, channel_y, c_double(sRun))
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_y, 0, c_double(rate))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_y, 0, c_double(2.5))
        dwf.FDwfAnalogOutTriggerSourceSet(hdwf, channel_y, c_byte(11))  # ExternalTrigger1

        # Buffer Configuration
        cBuffer_x = c_int(0)
        cBuffer_y = c_int(0)

        dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_x, 0, 0, byref(cBuffer_x))
        dwf.FDwfAnalogOutNodeDataInfo(hdwf, channel_y, 0, 0, byref(cBuffer_y))

        cBuffer_x.value = min(cBuffer_x.value, voltage_x.size)
        cBuffer_y.value = min(cBuffer_y.value, voltage_y.size)

        dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_x, 0, n_voltage_x, cBuffer_x)
        dwf.FDwfAnalogOutNodeDataSet(hdwf, channel_y, 0, n_voltage_y, cBuffer_y)

        # Enable Channels (waiting for trigger)
        dwf.FDwfAnalogOutConfigure(hdwf, channel_x, c_int(1))
        dwf.FDwfAnalogOutConfigure(hdwf, channel_y, c_int(1))

        print("Waiting for trigger...")

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
