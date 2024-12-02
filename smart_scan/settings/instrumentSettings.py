from smart_scan.settings import instrumentSettingsDefaults as instrSettDefault
from smart_scan.helpers.class_helpers import Singleton


class instrumentSettings(metaclass=Singleton):
    """This is the singleton instrumentSettings class, where the only instance of the instrumentSettings is."""

    def __init__(self) -> None:
        self._galvo_calibration = instrSettDefault.GALVO_CALIBRATION
        self._galvo_maxV = instrSettDefault.GALVO_MAXV
        self._galvo_minV = instrSettDefault.GALVO_MINV

    @property
    def galvo_calibration(self):
        return self._galvo_calibration
    
    @property
    def galvo_maxV(self):
        """The maximum V for the galvo mirrors [V]"""
        return self._galvo_maxV
    
    @property
    def galvo_minV(self):
        """The minimum V for the galvo mirrors [V]"""
        return self._galvo_minV

    # @galvo_calibration.setter
    # def slm(self, value):
    #     self._galvo_calibration = value
