import datetime
import os
from pathlib import Path

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
unique_log_file = Path(
    os.path.expanduser(
        f"~\\AppData\\Local\\pymmcore-plus\\pymmcore-plus\\logs\\pymmcore-plus_{timestamp}.log"
    )
)
os.environ["PYMM_LOG_FILE"] = str(unique_log_file)
