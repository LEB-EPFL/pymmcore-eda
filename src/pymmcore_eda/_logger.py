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
my_info_format = formatter.FORMATS[logging.INFO].replace(formatter.grey,
                                                         formatter.dark_grey)
formatter.FORMATS[logging.INFO] = my_info_format

def configure_logging():
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # automatically log to stderr
    if sys.stderr:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel('INFO')
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)

configure_logging()
