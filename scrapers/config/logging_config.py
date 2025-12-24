"""
Centralized logging configuration for all scrapers
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional


def add_logging_args(parser: argparse.ArgumentParser) -> None:
    """
    Add standard logging arguments (-v, -d) to an argument parser.

    Args:
        parser: ArgumentParser instance to add arguments to

    Usage:
        parser = argparse.ArgumentParser(description="My scraper")
        add_logging_args(parser)
        args = parser.parse_args()
        setup_logging_from_args(args)
    """
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (INFO level)"
    )
    group.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug output (DEBUG level)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional file to write logs to"
    )


def setup_logging_from_args(args: argparse.Namespace) -> None:
    """
    Configure logging based on parsed command-line arguments.

    Args:
        args: Parsed arguments from ArgumentParser with add_logging_args()
    """
    if args.debug:
        level = "DEBUG"
    elif args.verbose:
        level = "INFO"
    else:
        level = "WARNING"

    log_file = getattr(args, 'log_file', None)
    setup_logging(level=level, log_file=log_file)


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