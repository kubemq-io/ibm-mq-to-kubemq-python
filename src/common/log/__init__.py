import os
from loguru import logger
import sys


def setup_logging():
    logger.remove()
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <magenta>{name}</magenta>.<blue>{file}:{line}</blue> (<cyan>{extra[module]}</cyan>) - <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )


BaseLogger = logger


def get_logger(name):
    if name:
        return BaseLogger.bind(module=name)
    return BaseLogger


setup_logging()
