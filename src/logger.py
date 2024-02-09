import logging
from pathlib import Path

__all__ = ('logger',)

log_level = logging.INFO
default_log_message_format: str = "%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s"
logging.basicConfig(level=log_level, format=default_log_message_format, datefmt="(%Y-%m-%d, %H:%M:S)")
# create a file hander for recording to a log file

logger = logging.getLogger('CEG7830-Final-Project')
file_handler = logging.FileHandler(Path.cwd().joinpath('CEG7830-Final-Project.log'))
logger.addHandler(file_handler)
