"""Logging configuration helpers."""

from __future__ import annotations

import logging.config


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
        "access": {
            "format": '%(asctime)s | %(levelname)s | %(client_ip)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}


def configure_logging() -> None:
    """Configure structured logging for the application."""
    logging.config.dictConfig(LOGGING_CONFIG)
