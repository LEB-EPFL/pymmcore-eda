from smart_scan.settings import instrumentSettingsDefaults as instrSettDefault
from smart_scan.helpers.class_helpers import Singleton


class instrumentSettings(metaclass=Singleton):
    """This is the singleton instrumentSettings class, where the only instance of the instrumentSettings is."""

    def __init__(self) -> None:
        self._galvo_calibration = instrSettDefault.GALVO_CALIBRATION

    @property
    def galvo_calibration(self):
        return self._galvo_calibration

    # @galvo_calibration.setter
    # def slm(self, value):
    #     self._galvo_calibration = value
