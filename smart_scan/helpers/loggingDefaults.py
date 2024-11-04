import logging
import os

# Constants for the loggingHelper
logFolderName = "Logs"
path = os.path.join(os.getcwd(), logFolderName)

level = logging.INFO
format = "%(levelname)s:%(message)s"
loggerName = "Log_Default"
baseFileName = "Log_"
fileName = "Default"
