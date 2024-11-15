import logging
import sys
from copy import deepcopy
from pymmcore_plus._logger import CustomFormatter

class MyCustomFormatter(CustomFormatter):
    FORMATS = deepcopy(CustomFormatter.FORMATS)  # Create a new copy of the formats dict

logger = logging.getLogger('pymmcore_eda ')
logger.propagate = False
logger.setLevel(logging.INFO)
formatter = MyCustomFormatter()
formatter.FORMATS[logging.INFO] = formatter.dark_grey + formatter._format + formatter.reset

def configure_logging():
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # automatically log to stderr
    if sys.stderr:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel('INFO')
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)