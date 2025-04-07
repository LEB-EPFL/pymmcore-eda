import logging
import os

import smart_scan.helpers.loggingDefaults as DEFAULT


# Helper to create loggers within the projects
def createLogger(
    level=DEFAULT.level,
    format=DEFAULT.format,
    loggerName=DEFAULT.loggerName,
    fileName=DEFAULT.fileName,
) -> logging:
    # creates the log folder if it doesn't exist
    if not os.path.exists(DEFAULT.path):
        os.mkdir(DEFAULT.logFolderName)

    try:
        logger = logging.getLogger(loggerName)
        logger.setLevel(level)
        formatter = logging.Formatter(format)
        file_handler = logging.FileHandler(
            os.path.join(DEFAULT.path, f"{DEFAULT.baseFileName}{fileName}")
        )
        file_handler.setLevel(level)

    except:  # create default logger
        logger = logging.getLogger(DEFAULT.loggerName)
        logger.setLevel(DEFAULT.level)
        formatter = logging.Formatter(DEFAULT.format)
        file_handler = logging.FileHandler(
            os.path.join(DEFAULT.path, f"{DEFAULT.baseFileName}{DEFAULT.fileName}")
        )
        file_handler.setLevel(DEFAULT.level)
    finally:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger


def displayMessage(message):
    print(message)
