#!/usr/bin/env python3

"""Stand-alone utility functions & classes for CustomCam."""

from pathlib import Path
import argparse
import datetime
import logging
import sys
import inspect

import CustomCam.filters as filters


class Colors:
    """ ANSI color codes """
    GREY = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[0;37m"
    BOLD_GRAY = "\033[1;30m"
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_PURPLE = "\033[1;35m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    RESET = "\033[0m"


class ColourFormatter(logging.Formatter):
    """Extend a logger with level-specific colours."""
    format = "%(message)s"

    FORMATS = {
        logging.DEBUG: Colors.GREY + format + Colors.RESET,
        logging.INFO: Colors.BLUE + format + Colors.RESET,
        logging.WARNING: Colors.YELLOW + format + Colors.RESET,
        logging.ERROR: Colors.RED + format + Colors.RESET,
        logging.CRITICAL: Colors.BOLD_RED + format + Colors.RESET
    }

    def format(self, record: logging.LogRecord) -> str:
        """Perform formatting for a given record.

        Args:
            record (logging.LogRecord): Log event record.

        Returns:
            str
        """
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        format_str = formatter.format(record)
        return format_str


def valid_filepath(path: str) -> Path:
    """Determine whether a provided str is a valid file path, return as a Path object if it does. Fast-fail if not.

    Args:
        path (str): File path for verification.

    Returns:
        Path

    Raises:
        SystemExit: If provided file path does not exist.
    """

    path = Path(path)
    if path.is_file():
        return path
    else:
        print(f"Provided filepath: {path} does not exist.")
        sys.exit()


def setup_logger(logger_name: str, log_to_file: bool = False, level: int = logging.INFO) -> logging.Logger:
    """Create and return logger.

    Args:
        logger_name (str): Name of logger.
        log_to_file (bool): Whether to create a logfile.
        level (int): Base level of logger (verbosity).

    Returns:
        logging.Logger
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # Console logger
    c_handler = logging.StreamHandler()
    c_handler.setLevel(level)
    c_handler.setFormatter(ColourFormatter())
    logger.addHandler(c_handler)

    # File logger
    if log_to_file:
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        f_handler = logging.FileHandler(f"{timestamp}-CustomCam.log")
        f_handler.setLevel(logging.DEBUG)
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        f_handler.setFormatter(f_format)
        logger.addHandler(f_handler)

    logger.debug("Logger set up successfully")

    return logger


def setup_argparse() -> argparse.Namespace:
    """Create argument parser, return user-provided (or default) arguments.

    Returns:
        argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description=f"{Colors.YELLOW}🎥 CustomCam. Extendable webcam customisation in Python.{Colors.RESET}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--input_camera", type=int, default=0, help="ID of webcam device")
    parser.add_argument("--output_camera", type=str, default="/dev/video2", help="Dummy output device")
    parser.add_argument("--pref_width", type=int, help="Overwrite camera width.", default=None)
    parser.add_argument("--pref_height", type=int, help="Overwrite camera height.", default=None)
    parser.add_argument("--pref_fps", type=int, help="Overwrite camera fps.", default=None)
    parser.add_argument("--filter", choices=dict(inspect.getmembers(filters, inspect.isclass)).keys()-{'Filter'},
                        default="NoFilter")
    parser.add_argument("--fps", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--logfile", action="store_true", help="Write log to disk.")
    args = parser.parse_args()

    return args
