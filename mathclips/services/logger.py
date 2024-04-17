import logging
from pathlib import Path
import sys

__all__ = ('logger',)

log_level = logging.INFO
default_log_message_format: str = "[mathclips] %(asctime)s %(levelname)-8s >> %(message)s"
logging.basicConfig(level = log_level)

def initialize_logger() -> logging.Logger:
    logger = logging.getLogger('mathclips')

    log_formatter = logging.Formatter(default_log_message_format)
    log_formatter.datefmt = "<%Y-%m-%d,%H:%M:%S>"
    stdout_console_handler = logging.StreamHandler(sys.stdout)
    stdout_console_handler.setLevel(logging.DEBUG)
    stdout_console_handler.setFormatter(log_formatter)

    stderr_console_handler = logging.StreamHandler(sys.stderr)
    stderr_console_handler.setLevel(logging.ERROR)
    stderr_console_handler.setFormatter(log_formatter)

    file_handler = logging.FileHandler(filename = Path.cwd().resolve().joinpath("mathclips.log"))
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_console_handler)
    logger.addHandler(stderr_console_handler)
    return logger

logger = initialize_logger()
