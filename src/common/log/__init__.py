import os
from loguru import logger
import sys


def setup_logging():
    logger.remove()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.add(
        sys.stdout, level=log_level, colorize=True, backtrace=True, diagnose=True
    )


BaseLogger = logger


def get_logger(name):
    return BaseLogger
