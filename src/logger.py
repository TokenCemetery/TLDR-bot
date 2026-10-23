"""
Logging configuration module.

Sets up application-wide logging with configurable log level.
Suppresses verbose HTTP client logs to reduce noise.
"""

import logging
import os


class CustomFormatter(logging.Formatter):
    """
    Custom log formatter that includes 'extra' fields.

    Appends extra keyword arguments to log messages in a structured format.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record including extra fields.

        Args:
            record: Log record to format.

        Returns:
            Formatted log message with extra fields appended.
        """
        base_message = super().format(record)
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "message",
            "asctime",
            "taskName",
        }
        extra_fields = {key: value for key, value in record.__dict__.items() if key not in standard_attrs and not key.startswith("_")}
        if extra_fields:
            extra_str = " ".join(f'{k}="{v}"' for k, v in extra_fields.items())
            return f"{base_message}: {extra_str}"
        return base_message


def configure_logging() -> None:
    """
    Configure application logging.

    Sets up:
    - Root logger with specified level from LOG_LEVEL env var
    - Custom format with timestamp, level, logger name, message, and extra fields
    - Custom formatter that includes 'extra' keyword arguments
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    logging.getLogger("httpx").setLevel(logging.WARNING)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        CustomFormatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(handler)
