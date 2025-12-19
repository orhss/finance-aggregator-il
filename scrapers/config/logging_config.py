"""
Centralized logging configuration for all scrapers
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
):
    """
    Configure logging for scrapers

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
        format_string: Custom format string
    """
    if format_string is None:
        format_string = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(filename)s:%(lineno)d - %(message)s'
        )

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    # Set third-party loggers to WARNING
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('imaplib').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {level}")