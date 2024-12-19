import logging
import os
from logging.config import dictConfig


def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"name": "%(name)s", "file": "%(filename)s:%(lineno)d", '
                '"message": "%(message)s"}',
            },
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": numeric_level,
            "handlers": ["console"],
        },
    }

    dictConfig(config)


def get_logger(name):
    return logging.getLogger(name)


setup_logging()
